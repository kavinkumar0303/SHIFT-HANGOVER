"""
fetch_activity.py - Data Ingestion, Timestamp Normalization & Shift Window Filtering

Handles:
- Resilient multi-source loading (Ticketing & Incident JSON datasets)
- Safe parsing & UTC normalization of ISO8601 timestamps
- Half-open shift window interval filtering: [shift_start, shift_end)
- Logging skipped/malformed records without crashing
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def parse_and_normalize_timestamp(ts_input: Any) -> Optional[datetime]:
    """
    Parses various timestamp representations and converts them to a
    timezone-aware UTC datetime.
    
    Returns:
        datetime with tzinfo=timezone.utc, or None if parsing fails.
    """
    if ts_input is None:
        return None
    
    if isinstance(ts_input, datetime):
        if ts_input.tzinfo is None:
            return ts_input.replace(tzinfo=timezone.utc)
        return ts_input.astimezone(timezone.utc)
    
    if isinstance(ts_input, (int, float)):
        try:
            return datetime.fromtimestamp(ts_input, tz=timezone.utc)
        except (ValueError, OSError, OverflowError) as e:
            logger.warning(f"Failed to parse numeric timestamp '{ts_input}': {e}")
            return None

    if not isinstance(ts_input, str):
        logger.warning(f"Unsupported timestamp type: {type(ts_input)} for value: {ts_input}")
        return None

    cleaned_str = ts_input.strip()
    if not cleaned_str:
        return None

    try:
        dt = date_parser.parse(cleaned_str)
        if dt.tzinfo is None:
            # If no timezone specified, assume UTC
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Convert timezone to UTC
            dt = dt.astimezone(timezone.utc)
        return dt
    except (ValueError, TypeError, OverflowError) as e:
        logger.warning(f"Malformed timestamp '{cleaned_str}' skipped safely: {e}")
        return None


def load_source_data(file_path: str, default_source_name: str = "Generic Source") -> List[Dict[str, Any]]:
    """
    Safely loads JSON data from a file path.
    Gracefully catches missing files, unreadable permissions, or malformed JSON
    without terminating the application.
    """
    if not os.path.exists(file_path):
        logger.warning(f"Source file not found: '{file_path}'. Proceeding with empty dataset.")
        print(f"[WARN] Source unreachable: '{file_path}' (File not found)", file=sys.stderr)
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                standardized = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    item_copy = dict(item)
                    # Standardize source
                    if "source" not in item_copy or not item_copy["source"]:
                        item_copy["source"] = default_source_name
                    # Standardize record_id
                    if "record_id" not in item_copy and "id" in item_copy:
                        item_copy["record_id"] = str(item_copy["id"])
                    # Standardize summary / title
                    if "summary" not in item_copy and "title" in item_copy:
                        item_copy["summary"] = item_copy["title"]
                    # Standardize details / notes
                    if "details" not in item_copy and "notes" in item_copy:
                        item_copy["details"] = item_copy["notes"]
                    standardized.append(item_copy)
                return standardized
            elif isinstance(data, dict):
                items = data.get("items") or data.get("tickets") or data.get("incidents") or [data]
                return [dict(i) for i in items if isinstance(i, dict)]
            else:
                logger.warning(f"Unexpected JSON root type in '{file_path}': {type(data)}")
                return []
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error in '{file_path}': {e}. Skipping source.")
        print(f"[WARN] Corrupted JSON in source: '{file_path}': {e}", file=sys.stderr)
        return []
    except Exception as e:
        logger.warning(f"Failed to read source file '{file_path}': {e}. Skipping source.")
        print(f"[WARN] Error reading source '{file_path}': {e}", file=sys.stderr)
        return []


def get_source_status(file_path: str, source_name: str) -> Dict[str, Any]:
    """
    Returns health status and available record count for a source.
    """
    if not os.path.exists(file_path):
        return {
            "name": source_name,
            "path": file_path,
            "connected": False,
            "status": "Unavailable (File not found)",
            "total_records": 0
        }
    try:
        records = load_source_data(file_path, source_name)
        return {
            "name": source_name,
            "path": file_path,
            "connected": True,
            "status": "Connected",
            "total_records": len(records)
        }
    except Exception as e:
        return {
            "name": source_name,
            "path": file_path,
            "connected": False,
            "status": f"Unavailable ({str(e)})",
            "total_records": 0
        }


def fetch_activities_from_db(
    shift_start: datetime,
    shift_end: datetime
) -> List[Dict[str, Any]]:
    """
    Fetches activity items directly from the active database (PostgreSQL / SQLite)
    and filters for events strictly within the half-open interval [shift_start, shift_end).
    """
    from database import get_all_activities_from_db, init_db, seed_data_from_json
    
    init_db()
    raw_records = get_all_activities_from_db()
    if not raw_records:
        seed_data_from_json()
        raw_records = get_all_activities_from_db()
    norm_start = parse_and_normalize_timestamp(shift_start)
    norm_end = parse_and_normalize_timestamp(shift_end)

    if not norm_start or not norm_end:
        raise ValueError("Failed to parse and normalize shift boundary timestamps.")

    if norm_start >= norm_end:
        raise ValueError(f"Invalid shift window: shift_start ({norm_start.isoformat()}) must be earlier than shift_end ({norm_end.isoformat()})")

    filtered_events = []

    for record in raw_records:
        rec_id = record.get("record_id") or record.get("id") or "UNKNOWN"
        raw_ts = record.get("timestamp") or record.get("created_at")
        event_dt = parse_and_normalize_timestamp(raw_ts)

        if event_dt is None:
            logger.warning(f"Record [{rec_id}] skipped: Malformed or unparseable timestamp '{raw_ts}'")
            continue

        # Half-open interval [shift_start, shift_end)
        if norm_start <= event_dt < norm_end:
            normalized_item = dict(record)
            normalized_item["normalized_dt"] = event_dt
            normalized_item["normalized_timestamp"] = event_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            normalized_item["timestamp_display"] = event_dt.strftime("%d %b %Y, %H:%M UTC")
            normalized_item["record_id"] = str(rec_id)
            normalized_item["source"] = record.get("source") or "Database"
            normalized_item["summary"] = record.get("summary") or record.get("title") or f"Activity on {rec_id}"
            normalized_item["status"] = record.get("status") or "unknown"
            filtered_events.append(normalized_item)

    filtered_events.sort(key=lambda x: x["normalized_dt"])
    return filtered_events


def fetch_activities(
    sources: Optional[List[Dict[str, str]]] = None,
    shift_start: datetime = None,
    shift_end: datetime = None,
    use_db: bool = False,
    db_path: str = "database/shift_handover.db"
) -> List[Dict[str, Any]]:
    """
    Fetches activity items either from SQLite database or from provided source paths.
    Applies timezone normalization and half-open shift window [shift_start, shift_end) filtering.
    """
    if use_db or sources is None or len(sources) == 0:
        return fetch_activities_from_db(shift_start, shift_end)

    norm_start = parse_and_normalize_timestamp(shift_start)
    norm_end = parse_and_normalize_timestamp(shift_end)

    if not norm_start or not norm_end:
        raise ValueError("Failed to parse and normalize shift boundary timestamps.")

    if norm_start >= norm_end:
        raise ValueError(f"Invalid shift window: shift_start ({norm_start.isoformat()}) must be earlier than shift_end ({norm_end.isoformat()})")

    filtered_events = []
    sources = sources or []

    for src_cfg in sources:
        path = src_cfg.get("path", "")
        default_name = src_cfg.get("name", "Unknown System")
        raw_records = load_source_data(path, default_source_name=default_name)

        for record in raw_records:
            rec_id = record.get("record_id") or record.get("id") or "UNKNOWN"
            raw_ts = record.get("timestamp") or record.get("created_at") or record.get("updated_at") or record.get("time")
            event_dt = parse_and_normalize_timestamp(raw_ts)

            if event_dt is None:
                logger.warning(f"Record [{rec_id}] skipped: Malformed or unparseable timestamp '{raw_ts}'")
                continue

            # Apply half-open interval filter: [shift_start, shift_end)
            if norm_start <= event_dt < norm_end:
                normalized_item = dict(record)
                normalized_item["normalized_dt"] = event_dt
                normalized_item["normalized_timestamp"] = event_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                try:
                    normalized_item["timestamp_display"] = event_dt.strftime("%d %b %Y, %H:%M UTC")
                except Exception:
                    normalized_item["timestamp_display"] = str(event_dt)
                
                normalized_item["record_id"] = str(rec_id)
                normalized_item["source"] = record.get("source") or default_name
                normalized_item["summary"] = record.get("summary") or record.get("title") or f"Activity on {rec_id}"
                normalized_item["status"] = record.get("status") or "unknown"
                filtered_events.append(normalized_item)
            else:
                logger.debug(f"Record [{rec_id}] at {event_dt.isoformat()} outside shift [{norm_start.isoformat()} -> {norm_end.isoformat()})")

    # Sort all events chronologically (handles out-of-order records)
    filtered_events.sort(key=lambda x: x["normalized_dt"])
    return filtered_events
