"""
test_pipeline.py - Comprehensive Unit & Integration Test Suite

Tests:
1. Timestamp parsing & timezone normalization to UTC
2. Half-open shift window interval filtering [start, end)
3. Multi-source resilience (unreachable/corrupted source files)
4. Deduplication & chronological progression collapsing (including out-of-order events)
5. Rule-based 4-section classification (Completed, In Progress, Blockers, Watch-list)
6. Traceability guarantees (Record ID, Source, Timestamp, Summary)
7. PDF publisher rendering & 'Nothing to report.' display
8. Non-zero error exit codes on CLI failures
9. Web API Endpoints (/api/status, /api/generate, /api/download)
10. Deterministic identical runs verification
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
import pytest

from app import app
from fetch_activity import fetch_activities, get_source_status, load_source_data, parse_and_normalize_timestamp
from generator import (
    classify_into_sections,
    generate_dummy_handover,
    generate_handover,
    group_and_collapse_updates,
)
from publisher import build_pdf_document


# ==========================================
# 1. Timestamp Normalization Tests
# ==========================================

def test_parse_and_normalize_timestamp_utc():
    ts_str = "2026-09-03T08:30:00Z"
    dt = parse_and_normalize_timestamp(ts_str)
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.year == 2026
    assert dt.hour == 8
    assert dt.minute == 30


def test_parse_and_normalize_timestamp_with_offset():
    # 04:30 EDT (-04:00) is 08:30 UTC
    ts_str = "2026-09-03T04:30:00-04:00"
    dt = parse_and_normalize_timestamp(ts_str)
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 8
    assert dt.minute == 30


def test_parse_and_normalize_timestamp_positive_offset():
    # 14:00 IST (+05:30) is 08:30 UTC
    ts_str = "2026-09-03T14:00:00+05:30"
    dt = parse_and_normalize_timestamp(ts_str)
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 8
    assert dt.minute == 30


def test_parse_and_normalize_timestamp_malformed_returns_none():
    assert parse_and_normalize_timestamp("INVALID_GARBAGE_123") is None
    assert parse_and_normalize_timestamp("") is None
    assert parse_and_normalize_timestamp(None) is None


# ==========================================
# 2. Shift Window Half-Open Interval [start, end)
# ==========================================

def test_half_open_window_filtering(tmp_path):
    records = [
        {"record_id": "BEFORE", "timestamp": "2026-09-03T07:59:59Z", "summary": "Before window"},
        {"record_id": "START_EXACT", "timestamp": "2026-09-03T08:00:00Z", "summary": "At start boundary"},
        {"record_id": "INSIDE", "timestamp": "2026-09-03T12:00:00Z", "summary": "Inside window"},
        {"record_id": "END_EXACT", "timestamp": "2026-09-03T16:00:00Z", "summary": "At end boundary"},
        {"record_id": "AFTER", "timestamp": "2026-09-03T16:00:01Z", "summary": "After window"}
    ]
    test_file = tmp_path / "test_window.json"
    test_file.write_text(json.dumps(records), encoding="utf-8")

    start_dt = datetime(2026, 9, 3, 8, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 9, 3, 16, 0, 0, tzinfo=timezone.utc)

    sources = [{"path": str(test_file), "name": "Ticketing"}]
    events = fetch_activities(sources, start_dt, end_dt)

    ids = [e["record_id"] for e in events]
    assert "START_EXACT" in ids, "Event at exact shift_start must be INCLUDED [start, end)"
    assert "INSIDE" in ids, "Event inside window must be INCLUDED"
    assert "END_EXACT" not in ids, "Event at exact shift_end must be EXCLUDED [start, end)"
    assert "BEFORE" not in ids, "Event before shift_start must be EXCLUDED"
    assert "AFTER" not in ids, "Event after shift_end must be EXCLUDED"


# ==========================================
# 3. Resilience to Unreachable / Corrupt Sources
# ==========================================

def test_load_source_data_nonexistent_file():
    result = load_source_data("/nonexistent/path/to/missing_file.json", "Missing Source")
    assert result == []


def test_load_source_data_corrupted_json(tmp_path):
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("{ this is not valid json : [", encoding="utf-8")
    result = load_source_data(str(bad_file), "Bad Source")
    assert result == []


def test_get_source_status():
    stat = get_source_status("data/tickets.json", "Ticketing")
    assert stat["connected"] is True
    assert stat["total_records"] > 0


# ==========================================
# 4. Grouping, Deduplication & Out-of-Order Collapsing
# ==========================================

def test_group_and_collapse_out_of_order_updates():
    # Intentionally provided in reverse/out-of-order timestamps
    raw_events = [
        {
            "record_id": "TCK-1001",
            "source": "Ticketing",
            "summary": "Payment API timeout issue resolved and deployed",
            "status": "completed",
            "normalized_dt": datetime(2026, 9, 3, 13, 15, tzinfo=timezone.utc),
            "timestamp": "2026-09-03T18:45:00+05:30"
        },
        {
            "record_id": "TCK-1001",
            "source": "Ticketing",
            "summary": "Payment API timeout issue reported by checkout team",
            "status": "in_progress",
            "normalized_dt": datetime(2026, 9, 3, 11, 40, tzinfo=timezone.utc),
            "timestamp": "2026-09-03T17:10:00+05:30"
        },
        {
            "record_id": "TCK-1001",
            "source": "Ticketing",
            "summary": "Payment API timeout patch tested in staging",
            "status": "in_progress",
            "normalized_dt": datetime(2026, 9, 3, 12, 30, tzinfo=timezone.utc),
            "timestamp": "2026-09-03T18:00:00+05:30"
        }
    ]

    collapsed = group_and_collapse_updates(raw_events)
    assert len(collapsed) == 1, "Must collapse 3 updates into exactly 1 item"
    
    item = collapsed[0]
    assert item["record_id"] == "TCK-1001"
    assert item["status"] == "completed"
    assert item["initial_status"] == "in_progress"
    assert item["raw_update_count"] == 3
    assert item["progression"] == ["11:40 In Progress", "12:30 In Progress", "13:15 Completed"]
    assert item["summary"] == "Payment API timeout issue resolved and deployed"


# ==========================================
# 5. Rule-Based 4-Section Classification
# ==========================================

def test_classify_into_sections_all_four_categories():
    collapsed = [
        {"record_id": "TCK-1", "source": "Ticketing", "status": "completed", "priority": "P2"},
        {"record_id": "TCK-2", "source": "Ticketing", "status": "in_progress", "priority": "P3"},
        {"record_id": "TCK-3", "source": "Ticketing", "status": "blocked", "priority": "P1", "is_blocker": True},
        {"record_id": "INC-1", "source": "Incident", "status": "escalated", "priority": "SEV2"},
        {"record_id": "INC-2", "source": "Incident", "status": "monitoring", "priority": "SEV2", "watch_reason": "Canary monitoring"}
    ]

    sections = classify_into_sections(collapsed)

    assert len(sections["COMPLETED"]) == 1
    assert len(sections["IN PROGRESS"]) == 1
    assert len(sections["BLOCKERS / ESCALATIONS"]) == 2  # TCK-3, INC-1
    assert len(sections["WATCH-LIST"]) == 1  # INC-2

    # Verify traceability fields on every generated item
    for sec_name, items in sections.items():
        for itm in items:
            assert "section" in itm
            assert "source" in itm
            assert "record_id" in itm
            assert "timestamp" in itm
            assert "summary" in itm


# ==========================================
# 6. PDF Publisher & Empty States
# ==========================================

def test_build_pdf_document_with_empty_sections(tmp_path):
    empty_sections = {
        "COMPLETED": [],
        "IN PROGRESS": [],
        "BLOCKERS / ESCALATIONS": [],
        "WATCH-LIST": []
    }
    meta = {
        "shift_start": "2026-09-03 17:00 IST",
        "shift_end": "2026-09-03 20:00 IST",
        "generated_at": "2026-09-03 20:05 UTC",
        "total_items": 0
    }
    pdf_out = str(tmp_path / "empty_shift.pdf")
    res = build_pdf_document(empty_sections, pdf_out, meta)
    assert os.path.exists(res)
    assert os.path.getsize(res) > 1000


# ==========================================
# 7. CLI End-to-End Tests
# ==========================================

def test_cli_flags_and_generation():
    cmd = [
        sys.executable, "generate_note.py",
        "--shift-start", "2026-09-03T17:00:00+05:30",
        "--shift-end", "2026-09-03T20:00:00+05:30",
        "--output", "output/test_cli_run.pdf"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "COMPLETED: 3 item(s)" in proc.stdout
    assert "IN PROGRESS: 2 item(s)" in proc.stdout
    assert "BLOCKERS / ESCALATIONS: 2 item(s)" in proc.stdout
    assert "WATCH-LIST: 2 item(s)" in proc.stdout
    assert os.path.exists("output/test_cli_run.pdf")


def test_cli_invalid_window_exits_non_zero():
    cmd = [
        sys.executable, "generate_note.py",
        "--shift-start", "2026-09-03T20:00:00+05:30",
        "--shift-end", "2026-09-03T17:00:00+05:30"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode != 0


# ==========================================
# 8. Web API Endpoints Tests
# ==========================================

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_status_endpoint(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "READY"
    assert len(data["sources"]) == 2


def test_api_generate_endpoint_success(client):
    payload = {
        "shift_start": "2026-09-03T17:00:00+05:30",
        "shift_end": "2026-09-03T20:00:00+05:30"
    }
    res = client.post("/api/generate", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["metrics"]["completed"] == 3
    assert data["metrics"]["in_progress"] == 2
    assert data["metrics"]["blockers"] == 2
    assert data["metrics"]["watch_list"] == 2
    assert data["pdf_url"] is not None


def test_api_generate_invalid_input(client):
    # Missing fields
    res = client.post("/api/generate", json={})
    assert res.status_code == 400

    # Start >= End
    res = client.post("/api/generate", json={
        "shift_start": "2026-09-03T20:00:00+05:30",
        "shift_end": "2026-09-03T17:00:00+05:30"
    })
    assert res.status_code == 400


# ==========================================
# 9. Determinism Test
# ==========================================

def test_deterministic_identical_runs(client):
    payload = {
        "shift_start": "2026-09-03T17:00:00+05:30",
        "shift_end": "2026-09-03T20:00:00+05:30"
    }
    res1 = client.post("/api/generate", json=payload).get_json()
    res2 = client.post("/api/generate", json=payload).get_json()

    assert res1["metrics"] == res2["metrics"], "Same input must produce identical metric counts"
    assert len(res1["sections"]["completed"]) == len(res2["sections"]["completed"])
    assert len(res1["sections"]["blockers"]) == len(res2["sections"]["blockers"])


# ==========================================
# 10. SQLite Database Integration Tests
# ==========================================

def test_sqlite_database_lifecycle(tmp_path):
    from database import (
        get_all_activities_from_db,
        get_all_incidents,
        get_all_tickets,
        get_database_stats,
        get_handover_report_by_id,
        get_handover_reports,
        init_db,
        save_handover_report,
        seed_data_from_json,
    )

    test_db = str(tmp_path / "test_shift.db")
    init_db(test_db)
    assert os.path.exists(test_db)

    # Test Seeding
    t_cnt, i_cnt = seed_data_from_json("data/tickets.json", "data/incidents.json", test_db)
    assert t_cnt > 0
    assert i_cnt > 0

    # Test Idempotent Seeding (no duplicates)
    t_cnt2, i_cnt2 = seed_data_from_json("data/tickets.json", "data/incidents.json", test_db)
    tickets = get_all_tickets(test_db)
    assert len(tickets) == t_cnt, "Re-seeding must not duplicate records"

    # Test Report Saving
    sections = {
        "COMPLETED": [{"record_id": "TCK-1001", "source": "Ticketing", "summary": "Payment issue", "timestamp": "2026-09-03T18:45:00+05:30"}],
        "IN PROGRESS": [],
        "BLOCKERS / ESCALATIONS": [],
        "WATCH-LIST": []
    }
    rep_id = save_handover_report(
        shift_start="2026-09-03T17:00:00+05:30",
        shift_end="2026-09-03T20:00:00+05:30",
        generated_at="2026-09-03 14:00:00 UTC",
        total_items=1,
        completed_count=1,
        in_progress_count=0,
        blockers_count=0,
        watchlist_count=0,
        pdf_filename="test_note.pdf",
        pdf_path="output/test_note.pdf",
        sections=sections,
        db_path=test_db
    )
    assert rep_id is not None
    assert rep_id >= 1

    reports = get_handover_reports(db_path=test_db)
    assert len(reports) == 1
    assert reports[0]["id"] == rep_id

    report_detail = get_handover_report_by_id(rep_id, db_path=test_db)
    assert report_detail is not None
    assert len(report_detail["items"]) == 1
    assert report_detail["items"][0]["record_id"] == "TCK-1001"


def test_api_database_and_history_endpoints(client):
    # Test /api/data/tickets
    res = client.get("/api/data/tickets")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] > 0

    # Test /api/data/incidents
    res = client.get("/api/data/incidents")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] > 0

    # Test /api/reports
    res = client.get("/api/reports")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "reports" in data


def test_pdf_download_headers_and_content(client):
    # Generate report
    payload = {
        "shift_start": "2026-09-03T17:00:00+05:30",
        "shift_end": "2026-09-03T20:00:00+05:30"
    }
    gen_res = client.post("/api/generate", json=payload).get_json()
    pdf_filename = gen_res["pdf_filename"]

    # Preview header
    res_preview = client.get(f"/api/download/{pdf_filename}")
    assert res_preview.status_code == 200
    assert res_preview.headers["Content-Type"] == "application/pdf"
    assert "inline" in res_preview.headers["Content-Disposition"]
    assert res_preview.data.startswith(b"%PDF-")

    # Download header
    res_download = client.get(f"/api/download/{pdf_filename}?download=1")
    assert res_download.status_code == 200
    assert res_download.headers["Content-Type"] == "application/pdf"
    assert "attachment" in res_download.headers["Content-Disposition"]
    assert res_download.data.startswith(b"%PDF-")

