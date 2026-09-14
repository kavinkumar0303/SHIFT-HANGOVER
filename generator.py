"""
generator.py - Shift Handover Record Deduplication, Collapsing & 4-Section Categorization

Enforces:
1. Grouping by (source, record_id)
2. Handling out-of-order updates by sorting chronologically
3. Collapsing multiple updates into a single progression item with the latest meaningful state
4. Rule-based categorization into exactly four required sections:
   - COMPLETED
   - IN PROGRESS
   - BLOCKERS / ESCALATIONS
   - WATCH-LIST
5. Guaranteeing full traceability (source, record_id, timestamp, summary, section)
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List


def group_and_collapse_updates(raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups raw activity events by (source, record_id), sorts updates chronologically,
    and collapses multiple updates into one single consolidated item with progression.
    """
    grouped = defaultdict(list)
    for event in raw_events:
        src = event.get("source", "Unknown System")
        rec_id = event.get("record_id", "Unknown")
        grouped[(src, rec_id)].append(event)

    collapsed_items = []

    for (src, rec_id), updates in grouped.items():
        # Sort chronologically (ensures out-of-order records are processed properly)
        sorted_updates = sorted(
            updates,
            key=lambda u: u.get("normalized_dt") or datetime.min.replace(tzinfo=timezone.utc)
        )

        first_update = sorted_updates[0]
        latest_update = sorted_updates[-1]

        # Build chronological progression trail
        progression = []
        for u in sorted_updates:
            raw_ts = u.get("timestamp")
            u_dt = u.get("normalized_dt")
            time_label = u_dt.strftime("%H:%M") if u_dt else "--:--"
            st = str(u.get("status", "update")).replace("_", " ").title()
            progression.append(f"{time_label} {st}")

        # Derive latest meaningful state
        latest_status = str(latest_update.get("status", "unknown")).strip()
        initial_status = str(first_update.get("status", "unknown")).strip()
        summary = latest_update.get("summary") or first_update.get("summary") or f"Activity on {rec_id}"
        priority = latest_update.get("priority") or latest_update.get("severity") or first_update.get("priority") or first_update.get("severity") or ""
        assignee = latest_update.get("assignee") or latest_update.get("service") or latest_update.get("incident_commander") or ""
        details = latest_update.get("details") or latest_update.get("notes") or first_update.get("details") or ""
        
        # Flags
        is_blocker = any(u.get("is_blocker") is True for u in sorted_updates) or "blocked" in latest_status.lower() or "escalated" in latest_status.lower()
        blocker_reason = next((u.get("blocker_reason") for u in reversed(sorted_updates) if u.get("blocker_reason")), None)
        watch_reason = next((u.get("watch_reason") for u in reversed(sorted_updates) if u.get("watch_reason")), None)

        display_ts = latest_update.get("timestamp") or latest_update.get("timestamp_display") or latest_update.get("normalized_timestamp", "N/A")

        evidence = {
            "source_id": rec_id,
            "source_system": src,
            "update_count": len(sorted_updates),
            "first_seen": first_update.get("timestamp") or (first_update.get("normalized_dt").isoformat() if first_update.get("normalized_dt") else "N/A"),
            "last_updated": latest_update.get("timestamp") or (latest_update.get("normalized_dt").isoformat() if latest_update.get("normalized_dt") else "N/A"),
            "all_updates": [
                {
                    "timestamp": u.get("timestamp") or u.get("normalized_timestamp") or "N/A",
                    "status": str(u.get("status", "unknown")).replace("_", " ").title(),
                    "summary": u.get("summary") or u.get("title") or "",
                    "details": u.get("details") or u.get("notes") or "",
                    "assignee": u.get("assignee") or u.get("service") or "",
                    "priority": u.get("priority") or u.get("severity") or ""
                }
                for u in sorted_updates
            ]
        }

        collapsed_item = {
            "record_id": rec_id,
            "source": src,
            "summary": summary,
            "status": latest_status,
            "initial_status": initial_status,
            "priority": priority,
            "assignee": assignee,
            "details": details,
            "is_blocker": is_blocker,
            "blocker_reason": blocker_reason,
            "watch_reason": watch_reason,
            "progression": progression,
            "evidence": evidence,
            "latest_dt": latest_update.get("normalized_dt"),
            "timestamp": display_ts,
            "raw_update_count": len(sorted_updates)
        }
        collapsed_items.append(collapsed_item)

    # Sort collapsed items by latest update timestamp descending
    collapsed_items.sort(
        key=lambda x: x.get("latest_dt") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )
    return collapsed_items


def classify_into_sections(collapsed_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorizes collapsed items into the four required sections:
    1. COMPLETED
    2. IN PROGRESS
    3. BLOCKERS / ESCALATIONS
    4. WATCH-LIST
    """
    sections = {
        "COMPLETED": [],
        "IN PROGRESS": [],
        "BLOCKERS / ESCALATIONS": [],
        "WATCH-LIST": []
    }

    COMPLETED_STATUSES = {"completed", "resolved", "closed", "done", "merged"}
    BLOCKER_STATUSES = {"blocked", "escalated", "blocker", "failed"}
    WATCH_STATUSES = {"monitoring", "watch", "canary", "mitigated"}

    for item in collapsed_items:
        status_norm = str(item.get("status", "")).strip().lower().replace("-", "_").replace(" ", "_")
        priority_norm = str(item.get("priority", "")).strip().lower()
        is_blocker_flag = item.get("is_blocker") is True or bool(item.get("blocker_reason"))
        watch_reason = item.get("watch_reason")

        item_copy = dict(item)
        if "timestamp" not in item_copy:
            item_copy["timestamp"] = item_copy.get("timestamp_display") or item_copy.get("normalized_timestamp") or "N/A"
        if "summary" not in item_copy:
            item_copy["summary"] = item_copy.get("title") or f"Activity on {item_copy.get('record_id', 'N/A')}"

        # 1. Blockers / Escalations (High operational urgency)
        if (
            is_blocker_flag or
            status_norm in BLOCKER_STATUSES or
            "blocked" in status_norm or
            "escalated" in status_norm or
            (priority_norm in {"sev1", "p1", "critical"} and status_norm not in COMPLETED_STATUSES and status_norm not in WATCH_STATUSES)
        ):
            item_copy["section"] = "BLOCKERS / ESCALATIONS"
            sections["BLOCKERS / ESCALATIONS"].append(item_copy)

        # 2. Watch-list (Monitoring, Canary, Post-mitigation verification)
        elif (
            bool(watch_reason) or
            status_norm in WATCH_STATUSES or
            "monitor" in status_norm or
            "watch" in status_norm or
            "canary" in status_norm
        ):
            item_copy["section"] = "WATCH-LIST"
            sections["WATCH-LIST"].append(item_copy)

        # 3. Completed
        elif (
            status_norm in COMPLETED_STATUSES or
            "resolved" in status_norm or
            "closed" in status_norm
        ):
            item_copy["section"] = "COMPLETED"
            sections["COMPLETED"].append(item_copy)

        # 4. In Progress (Active work)
        else:
            item_copy["section"] = "IN PROGRESS"
            sections["IN PROGRESS"].append(item_copy)

    return sections


def generate_handover(raw_events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    End-to-end generator pipeline: deduplicates, collapses, and classifies raw events.
    """
    collapsed = group_and_collapse_updates(raw_events)
    return classify_into_sections(collapsed)


def generate_dummy_handover() -> Dict[str, List[Dict[str, Any]]]:
    """
    Verification dummy generator.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "COMPLETED": [
            {
                "section": "COMPLETED",
                "record_id": "TCK-1001",
                "source": "Ticketing",
                "timestamp": now_str,
                "summary": "Payment API timeout issue resolved",
                "status": "completed",
                "priority": "P1",
                "assignee": "Alex Rivera",
                "progression": ["17:10 In Progress", "18:00 In Progress", "18:45 Completed"]
            }
        ],
        "IN PROGRESS": [
            {
                "section": "IN PROGRESS",
                "record_id": "TCK-1002",
                "source": "Ticketing",
                "timestamp": now_str,
                "summary": "Migrate Stripe webhook endpoints to v3 schema",
                "status": "in_progress",
                "priority": "P3",
                "assignee": "Sam Chen",
                "progression": ["17:20 In Progress", "19:10 In Progress"]
            }
        ],
        "BLOCKERS / ESCALATIONS": [
            {
                "section": "BLOCKERS / ESCALATIONS",
                "record_id": "INC-2003",
                "source": "Incident",
                "timestamp": now_str,
                "summary": "Third-party SMS OTP delivery degradation",
                "status": "escalated",
                "priority": "SEV2",
                "assignee": "auth-notifications",
                "progression": ["18:25 Escalated"]
            }
        ],
        "WATCH-LIST": []  # Empty section tests 'Nothing to report.'
    }
