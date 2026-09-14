#!/usr/bin/env python3
"""
generate_note.py - Shift Handover Note Generator CLI Application

Orchestrates the complete deterministic pipeline:
CLI Trigger
  → fetch-activity
  → shift-window filtering
  → timezone normalization
  → generator
  → deduplication
  → four sections
  → publisher
  → single PDF
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from fetch_activity import fetch_activities, parse_and_normalize_timestamp
from generator import generate_dummy_handover, generate_handover
from publisher import build_pdf_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("generate_note")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Shift Handover Note Generator - Generates executive-grade PDF handover reports."
    )
    # Support both --shift-start/--shift-end and --start/--end
    parser.add_argument(
        "--shift-start", "--start",
        dest="shift_start",
        required=True,
        help="Shift start timestamp (ISO8601, e.g. 2026-09-03T17:00:00+05:30 or '2026-09-03 17:00:00')"
    )
    parser.add_argument(
        "--shift-end", "--end",
        dest="shift_end",
        required=True,
        help="Shift end timestamp (ISO8601, e.g. 2026-09-03T20:00:00+05:30 or '2026-09-03 20:00:00')"
    )
    parser.add_argument(
        "--tickets-file",
        default="data/tickets.json",
        help="Path to ticketing system JSON feed (default: data/tickets.json)"
    )
    parser.add_argument(
        "--incidents-file",
        default="data/incidents.json",
        help="Path to incident management JSON feed (default: data/incidents.json)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to output PDF document (default: output/handover_note_<start>_<end>.pdf)"
    )
    parser.add_argument(
        "--dummy",
        action="store_true",
        help="Run in dummy mode (generates verification dummy item for pipeline testing)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging"
    )
    return parser.parse_args()


def run_pipeline(
    start_str: str,
    end_str: str,
    tickets_path: str = "data/tickets.json",
    incidents_path: str = "data/incidents.json",
    output_pdf_path: str = None,
    dummy_mode: bool = False,
    verbose: bool = False
) -> str:
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 1. Parse & Normalize shift window
    start_dt = parse_and_normalize_timestamp(start_str)
    end_dt = parse_and_normalize_timestamp(end_str)

    if not start_dt:
        print(f"[ERROR] Invalid shift start timestamp: '{start_str}'", file=sys.stderr)
        sys.exit(2)

    if not end_dt:
        print(f"[ERROR] Invalid shift end timestamp: '{end_str}'", file=sys.stderr)
        sys.exit(2)

    if start_dt >= end_dt:
        print(f"[ERROR] Shift start ({start_dt.isoformat()}) must be earlier than shift end ({end_dt.isoformat()})", file=sys.stderr)
        sys.exit(2)

    start_iso = start_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    end_iso = end_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Determine output path
    if not output_pdf_path:
        out_dir = "output"
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError:
            out_dir = "/tmp/output"
            os.makedirs(out_dir, exist_ok=True)
        filename_start = start_dt.strftime("%Y%m%d_%H%M%S")
        filename_end = end_dt.strftime("%Y%m%d_%H%M%S")
        output_pdf_path = os.path.join(out_dir, f"handover_note_{filename_start}_to_{filename_end}.pdf")

    print("=" * 65)
    print("🚀 SHIFT//HANDOVER — Automated Shift Handover Intelligence")
    print(f"Shift Window: {start_str} -> {end_str}")
    print(f"Normalized UTC: {start_iso} -> {end_iso}")
    print(f"Mode: {'DUMMY PIPELINE VERIFICATION' if dummy_mode else 'RULE-BASED DETERMINISTIC GENERATION'}")
    print("=" * 65)

    # 2. Activity Fetching & Normalization
    if dummy_mode:
        print("\n[Stage 1-3] Running Dummy Pipeline...")
        sections = generate_dummy_handover()
        total_raw_events = 3
    else:
        sources = [
            {"path": tickets_path, "name": "Ticketing"},
            {"path": incidents_path, "name": "Incident"}
        ]
        print(f"\n[Stage 1] Ingesting & normalizing from {len(sources)} data sources...")
        raw_events = fetch_activities(sources, start_dt, end_dt)
        total_raw_events = len(raw_events)
        print(f"         Ingested & filtered {total_raw_events} raw event(s) inside shift window.")

        # 3. Generator (Deduplication, Collapsing & 4-Section Classification)
        print("\n[Stage 2] Grouping by (source, record_id), collapsing progression & classifying...")
        sections = generate_handover(raw_events)

    # Print Terminal Breakdown
    print("\n[Stage 3] Section Breakdown:")
    for sec_name in ["COMPLETED", "IN PROGRESS", "BLOCKERS / ESCALATIONS", "WATCH-LIST"]:
        items = sections.get(sec_name, [])
        print(f"  • {sec_name}: {len(items)} item(s)")
        if not items:
            print("     - No activity recorded in this category during the selected shift.")
        for itm in items:
            rec_id = itm.get("record_id", "N/A")
            summary = itm.get("summary", "")
            src = itm.get("source", "N/A")
            ts = itm.get("timestamp", "")
            prog = itm.get("progression", [])
            prog_text = f" [{' -> '.join(prog)}]" if len(prog) > 1 else ""
            print(f"     - [{rec_id}] ({src}) {summary}{prog_text} | {ts}")

    # 4. Publisher (PDF Export)
    print(f"\n[Stage 4] Publishing Single PDF to '{output_pdf_path}'...")
    shift_meta = {
        "shift_start": f"{start_str} ({start_iso})",
        "shift_end": f"{end_str} ({end_iso})",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_items": total_raw_events
    }

    try:
        final_pdf = build_pdf_document(sections, output_pdf_path, shift_meta)
        print(f"✅ Handover Note PDF successfully generated: {final_pdf}\n")

        # Save into SQLite Database
        try:
            from database import save_handover_report
            comp_cnt = len(sections.get("COMPLETED", []))
            in_prog_cnt = len(sections.get("IN PROGRESS", []))
            block_cnt = len(sections.get("BLOCKERS / ESCALATIONS", []))
            watch_cnt = len(sections.get("WATCH-LIST", []))

            report_id = save_handover_report(
                shift_start=start_str,
                shift_end=end_str,
                generated_at=shift_meta["generated_at"],
                total_items=total_raw_events,
                completed_count=comp_cnt,
                in_progress_count=in_prog_cnt,
                blockers_count=block_cnt,
                watchlist_count=watch_cnt,
                pdf_filename=os.path.basename(final_pdf),
                pdf_path=final_pdf,
                sections=sections
            )
            print(f"📦 Handover Report stored in SQLite (Report ID: #{report_id})")
        except Exception as db_err:
            logger.warning(f"Could not persist report to SQLite: {db_err}")

        return final_pdf
    except Exception as e:
        print(f"\n❌ FATAL: Document export failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    run_pipeline(
        start_str=args.shift_start,
        end_str=args.shift_end,
        tickets_path=args.tickets_file,
        incidents_path=args.incidents_file,
        output_pdf_path=args.output,
        dummy_mode=args.dummy,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
