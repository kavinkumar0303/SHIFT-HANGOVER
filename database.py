"""
database.py - Unified PostgreSQL (Supabase) & SQLite Database Layer

Manages connection lifecycle, schema initialization, JSON seed syncing (UPSERT),
activity querying, and report history persistence.
"""

import json
import logging
import os
import sqlite3
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("database")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Read DATABASE_URL from environment; default to empty to avoid network timeouts on unconfigured deployments
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def get_default_db_path() -> str:
    """Returns a safe, writable SQLite database path."""
    env_path = os.getenv("SQLITE_DB_PATH")
    if env_path:
        return env_path

    # On Vercel / AWS Lambda, only /tmp is writable
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/shift_handover.db"

    try:
        local_dir = os.path.join(BASE_DIR, "database")
        os.makedirs(local_dir, exist_ok=True)
        test_file = os.path.join(local_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return os.path.join(local_dir, "shift_handover.db")
    except (OSError, IOError, PermissionError):
        return "/tmp/shift_handover.db"


try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def is_postgres() -> bool:
    return bool(DATABASE_URL and DATABASE_URL.startswith(("postgresql://", "postgres://")) and HAS_PSYCOPG2)


def get_connection(db_path: Optional[str] = None):
    """
    Returns an open database connection:
    - If explicit SQLite db_path is passed, uses SQLite
    - Otherwise uses PostgreSQL if DATABASE_URL is configured and reachable
    - Falls back to SQLite if PostgreSQL fails
    """
    if db_path:
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir:
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError:
                pass
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn, False

    if is_postgres():
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=3)
            conn.autocommit = True
            return conn, True
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite.")

    actual_db_path = get_default_db_path()
    db_dir = os.path.dirname(os.path.abspath(actual_db_path))
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError:
            pass
    conn = sqlite3.connect(actual_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn, False


def init_db(db_path: Optional[str] = None) -> None:
    """Creates tables if they do not exist."""
    try:
        conn, is_pg = get_connection(db_path)
        try:
            cur = conn.cursor()
            if is_pg:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id SERIAL PRIMARY KEY,
                        record_id TEXT UNIQUE NOT NULL,
                        summary TEXT NOT NULL,
                        status TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        source TEXT DEFAULT 'Ticketing',
                        priority TEXT,
                        description TEXT,
                        created_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS incidents (
                        id SERIAL PRIMARY KEY,
                        record_id TEXT UNIQUE NOT NULL,
                        summary TEXT NOT NULL,
                        status TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        source TEXT DEFAULT 'Incident',
                        severity TEXT,
                        description TEXT,
                        created_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS handover_reports (
                        id SERIAL PRIMARY KEY,
                        shift_start TEXT NOT NULL,
                        shift_end TEXT NOT NULL,
                        generated_at TEXT NOT NULL,
                        total_items INTEGER DEFAULT 0,
                        completed_count INTEGER DEFAULT 0,
                        in_progress_count INTEGER DEFAULT 0,
                        blockers_count INTEGER DEFAULT 0,
                        watchlist_count INTEGER DEFAULT 0,
                        pdf_filename TEXT,
                        pdf_path TEXT
                    );
                    CREATE TABLE IF NOT EXISTS handover_items (
                        id SERIAL PRIMARY KEY,
                        report_id INTEGER NOT NULL REFERENCES handover_reports(id) ON DELETE CASCADE,
                        section TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        source TEXT NOT NULL,
                        record_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );
                """)
            else:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_id TEXT UNIQUE NOT NULL,
                        summary TEXT NOT NULL,
                        status TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        source TEXT DEFAULT 'Ticketing',
                        priority TEXT,
                        description TEXT,
                        created_at TEXT
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS incidents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_id TEXT UNIQUE NOT NULL,
                        summary TEXT NOT NULL,
                        status TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        source TEXT DEFAULT 'Incident',
                        severity TEXT,
                        description TEXT,
                        created_at TEXT
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS handover_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shift_start TEXT NOT NULL,
                        shift_end TEXT NOT NULL,
                        generated_at TEXT NOT NULL,
                        total_items INTEGER DEFAULT 0,
                        completed_count INTEGER DEFAULT 0,
                        in_progress_count INTEGER DEFAULT 0,
                        blockers_count INTEGER DEFAULT 0,
                        watchlist_count INTEGER DEFAULT 0,
                        pdf_filename TEXT,
                        pdf_path TEXT
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS handover_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_id INTEGER NOT NULL REFERENCES handover_reports(id) ON DELETE CASCADE,
                        section TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        source TEXT NOT NULL,
                        record_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );
                """)
                conn.commit()
        finally:
            conn.close()
    except Exception as err:
        logger.error(f"Error in init_db: {err}")


def resolve_data_path(file_path: Optional[str], default_rel: str) -> str:
    """Helper to resolve JSON data file paths safely."""
    if file_path and os.path.exists(file_path):
        return file_path
    if file_path and not os.path.isabs(file_path):
        alt = os.path.join(BASE_DIR, file_path)
        if os.path.exists(alt):
            return alt
    default_path = os.path.join(BASE_DIR, default_rel)
    if os.path.exists(default_path):
        return default_path
    return file_path or default_path


def seed_data_from_json(
    tickets_json_path: Optional[str] = None,
    incidents_json_path: Optional[str] = None,
    db_path: Optional[str] = None
) -> Tuple[int, int]:
    """
    Seeds initial dataset from JSON feeds into PostgreSQL / SQLite with idempotent UPSERTs.
    Returns (tickets_count, incidents_count).
    """
    init_db(db_path)
    conn, is_pg = get_connection(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    actual_tickets_path = resolve_data_path(tickets_json_path, "data/tickets.json")
    actual_incidents_path = resolve_data_path(incidents_json_path, "data/incidents.json")

    try:
        cur = conn.cursor()

        # 1. Seed Tickets
        if os.path.exists(actual_tickets_path):
            try:
                with open(actual_tickets_path, "r", encoding="utf-8") as f:
                    tickets = json.load(f)
                    if isinstance(tickets, list):
                        distinct_tickets = {}
                        for item in tickets:
                            rec_id = item.get("record_id") or item.get("id")
                            if not rec_id:
                                continue
                            summary = item.get("summary") or item.get("title") or "No Summary"
                            status = item.get("status") or "open"
                            ts = item.get("timestamp") or item.get("created_at") or now_iso
                            src = item.get("source") or "Ticketing"
                            priority = item.get("priority") or item.get("severity") or ""
                            desc = item.get("details") or item.get("description") or ""
                            distinct_tickets[str(rec_id)] = (str(rec_id), summary, status, ts, src, priority, desc, now_iso)

                        ticket_tuples = list(distinct_tickets.values())
                        if is_pg and ticket_tuples:
                            from psycopg2.extras import execute_values
                            execute_values(
                                cur,
                                """
                                INSERT INTO tickets (record_id, summary, status, timestamp, source, priority, description, created_at)
                                VALUES %s
                                ON CONFLICT (record_id) DO UPDATE SET
                                    summary = EXCLUDED.summary,
                                    status = EXCLUDED.status,
                                    timestamp = EXCLUDED.timestamp,
                                    source = EXCLUDED.source,
                                    priority = EXCLUDED.priority,
                                    description = EXCLUDED.description;
                                """,
                                ticket_tuples
                            )
                        else:
                            for t in ticket_tuples:
                                cur.execute("""
                                    INSERT INTO tickets (record_id, summary, status, timestamp, source, priority, description, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(record_id) DO UPDATE SET
                                        summary = excluded.summary,
                                        status = excluded.status,
                                        timestamp = excluded.timestamp,
                                        source = excluded.source,
                                        priority = excluded.priority,
                                        description = excluded.description;
                                """, t)
            except Exception as e:
                logger.warning(f"Failed to seed tickets from '{actual_tickets_path}': {e}")

        # 2. Seed Incidents
        if os.path.exists(actual_incidents_path):
            try:
                with open(actual_incidents_path, "r", encoding="utf-8") as f:
                    incidents = json.load(f)
                    if isinstance(incidents, list):
                        distinct_incidents = {}
                        for item in incidents:
                            rec_id = item.get("record_id") or item.get("id")
                            if not rec_id:
                                continue
                            summary = item.get("summary") or item.get("title") or "No Summary"
                            status = item.get("status") or "investigating"
                            ts = item.get("timestamp") or item.get("created_at") or now_iso
                            src = item.get("source") or "Incident"
                            severity = item.get("severity") or item.get("priority") or ""
                            desc = item.get("details") or item.get("description") or ""
                            distinct_incidents[str(rec_id)] = (str(rec_id), summary, status, ts, src, severity, desc, now_iso)

                        incident_tuples = list(distinct_incidents.values())
                        if is_pg and incident_tuples:
                            from psycopg2.extras import execute_values
                            execute_values(
                                cur,
                                """
                                INSERT INTO incidents (record_id, summary, status, timestamp, source, severity, description, created_at)
                                VALUES %s
                                ON CONFLICT (record_id) DO UPDATE SET
                                    summary = EXCLUDED.summary,
                                    status = EXCLUDED.status,
                                    timestamp = EXCLUDED.timestamp,
                                    source = EXCLUDED.source,
                                    severity = EXCLUDED.severity,
                                    description = EXCLUDED.description;
                                """,
                                incident_tuples
                            )
                        else:
                            for inc in incident_tuples:
                                cur.execute("""
                                    INSERT INTO incidents (record_id, summary, status, timestamp, source, severity, description, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(record_id) DO UPDATE SET
                                        summary = excluded.summary,
                                        status = excluded.status,
                                        timestamp = excluded.timestamp,
                                        source = excluded.source,
                                        severity = excluded.severity,
                                        description = excluded.description;
                                """, inc)
            except Exception as e:
                logger.warning(f"Failed to seed incidents from '{actual_incidents_path}': {e}")

        if not is_pg:
            conn.commit()

        cur.execute("SELECT COUNT(*) FROM tickets;")
        t_cnt_row = cur.fetchone()
        t_cnt = t_cnt_row[0] if t_cnt_row else 0
        cur.execute("SELECT COUNT(*) FROM incidents;")
        i_cnt_row = cur.fetchone()
        i_cnt = i_cnt_row[0] if i_cnt_row else 0
        return t_cnt, i_cnt
    finally:
        conn.close()


def get_all_tickets(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all tickets from the database."""
    init_db(db_path)
    conn, is_pg = get_connection(db_path)
    try:
        if is_pg:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM tickets ORDER BY timestamp ASC;")
            return [dict(row) for row in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM tickets ORDER BY timestamp ASC;")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_all_incidents(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all incidents from the database."""
    init_db(db_path)
    conn, is_pg = get_connection(db_path)
    try:
        if is_pg:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM incidents ORDER BY timestamp ASC;")
            return [dict(row) for row in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM incidents ORDER BY timestamp ASC;")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_all_activities_from_db(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves combined tickets and incidents from the database."""
    return get_all_tickets(db_path) + get_all_incidents(db_path)


def save_handover_report(
    shift_start: str,
    shift_end: str,
    generated_at: str,
    total_items: int,
    completed_count: int,
    in_progress_count: int,
    blockers_count: int,
    watchlist_count: int,
    pdf_filename: str,
    pdf_path: str,
    sections: Dict[str, List[Dict[str, Any]]],
    db_path: Optional[str] = None
) -> int:
    """
    Saves a generated handover report and its individual items into the database.
    Returns the newly inserted report ID.
    """
    init_db(db_path)
    conn, is_pg = get_connection(db_path)
    try:
        cur = conn.cursor()
        if is_pg:
            cur.execute("""
                INSERT INTO handover_reports (
                    shift_start, shift_end, generated_at, total_items,
                    completed_count, in_progress_count, blockers_count, watchlist_count,
                    pdf_filename, pdf_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                shift_start, shift_end, generated_at, total_items,
                completed_count, in_progress_count, blockers_count, watchlist_count,
                pdf_filename, pdf_path
            ))
            report_id = cur.fetchone()[0]

            item_tuples = []
            for section_name, items in sections.items():
                for itm in items:
                    item_tuples.append((
                        report_id,
                        section_name,
                        itm.get("summary") or "No Summary",
                        itm.get("source") or "Unknown",
                        itm.get("record_id") or "UNKNOWN",
                        itm.get("timestamp") or generated_at
                    ))

            if item_tuples:
                from psycopg2.extras import execute_values
                execute_values(
                    cur,
                    """
                    INSERT INTO handover_items (report_id, section, summary, source, record_id, timestamp)
                    VALUES %s;
                    """,
                    item_tuples
                )
        else:
            cur.execute("""
                INSERT INTO handover_reports (
                    shift_start, shift_end, generated_at, total_items,
                    completed_count, in_progress_count, blockers_count, watchlist_count,
                    pdf_filename, pdf_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                shift_start, shift_end, generated_at, total_items,
                completed_count, in_progress_count, blockers_count, watchlist_count,
                pdf_filename, pdf_path
            ))
            report_id = cur.lastrowid

            for section_name, items in sections.items():
                for itm in items:
                    cur.execute("""
                        INSERT INTO handover_items (
                            report_id, section, summary, source, record_id, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?);
                    """, (
                        report_id,
                        section_name,
                        itm.get("summary") or "No Summary",
                        itm.get("source") or "Unknown",
                        itm.get("record_id") or "UNKNOWN",
                        itm.get("timestamp") or generated_at
                    ))
            conn.commit()

        return report_id
    finally:
        conn.close()


def get_handover_reports(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves list of previous handover reports."""
    init_db(db_path)
    conn, is_pg = get_connection(db_path)
    try:
        if is_pg:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM handover_reports ORDER BY id DESC LIMIT %s;", (limit,))
            return [dict(row) for row in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM handover_reports ORDER BY id DESC LIMIT ?;", (limit,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_handover_report_by_id(report_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single handover report along with all its classified items."""
    init_db(db_path)
    conn, is_pg = get_connection(db_path)
    try:
        if is_pg:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM handover_reports WHERE id = %s;", (report_id,))
            report_row = cur.fetchone()
            if not report_row:
                return None
            report = dict(report_row)
            cur.execute("SELECT * FROM handover_items WHERE report_id = %s ORDER BY id ASC;", (report_id,))
            items = [dict(r) for r in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM handover_reports WHERE id = ?;", (report_id,))
            report_row = cur.fetchone()
            if not report_row:
                return None
            report = dict(report_row)
            cur.execute("SELECT * FROM handover_items WHERE report_id = ? ORDER BY id ASC;", (report_id,))
            items = [dict(r) for r in cur.fetchall()]

        sections = {
            "COMPLETED": [],
            "IN PROGRESS": [],
            "BLOCKERS / ESCALATIONS": [],
            "WATCH-LIST": []
        }
        for itm in items:
            sec = itm.get("section", "IN PROGRESS")
            if sec in sections:
                sections[sec].append(itm)
            else:
                sections[sec] = [itm]

        report["items"] = items
        report["sections"] = sections
        return report
    finally:
        conn.close()


def get_database_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Returns database connection status and record counts safely."""
    try:
        init_db(db_path)
        conn, is_pg = get_connection(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tickets;")
            t_row = cur.fetchone()
            t_count = t_row[0] if t_row else 0
            cur.execute("SELECT COUNT(*) FROM incidents;")
            i_row = cur.fetchone()
            i_count = i_row[0] if i_row else 0
            cur.execute("SELECT COUNT(*) FROM handover_reports;")
            r_row = cur.fetchone()
            r_count = r_row[0] if r_row else 0
            cur.execute("SELECT COUNT(*) FROM handover_items;")
            items_row = cur.fetchone()
            items_count = items_row[0] if items_row else 0

            db_type = "PostgreSQL (Cloud)" if is_pg else "SQLite"
            if is_pg and DATABASE_URL:
                try:
                    parsed = urllib.parse.urlparse(DATABASE_URL)
                    db_target = f"{parsed.hostname}:{parsed.port or 5432}{parsed.path}"
                except Exception:
                    db_target = "PostgreSQL (Connected)"
            else:
                db_target = db_path or get_default_db_path()

            return {
                "connected": True,
                "engine": db_type,
                "database_target": db_target,
                "tickets_count": t_count,
                "incidents_count": i_count,
                "reports_count": r_count,
                "handover_items_count": items_count
            }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {
            "connected": False,
            "engine": "PostgreSQL (Cloud)" if is_postgres() else "SQLite",
            "error": "Database unavailable",
            "tickets_count": 0,
            "incidents_count": 0,
            "reports_count": 0,
            "handover_items_count": 0
        }


if __name__ == "__main__":
    print("🚀 Initializing Shift Handover Database...")
    init_db()
    t_num, i_num = seed_data_from_json()
    stats = get_database_stats()
    print("\n✅ Database initialized and seeded successfully.")
    print(f"Engine: {stats['engine']}")
    print(f"Target: {stats['database_target']}")
    print(f"Tickets: {stats['tickets_count']}")
    print(f"Incidents: {stats['incidents_count']}")
    print(f"Reports: {stats['reports_count']}")
