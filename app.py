"""
app.py - Flask Web Backend for Shift Handover Note Generator

Provides:
- GET / : Web Dashboard Interface
- GET /login : NOC Operator Login Page
- GET /api/status : Data Sources and System Health Monitor
- POST /api/generate : Trigger Ingestion, Deduplication, 4-Section Generation & PDF Export
- GET /api/download/<filename> : View/Download Generated PDF Document
- GET /api/reports : Historical generated reports
- GET /api/reports/<int:report_id> : Individual report details
- GET /api/data/tickets : Stored tickets
- GET /api/data/incidents : Stored incidents
- GET /static/<filename> : Static CSS / JS / Assets
"""

import logging
import os
import sys
from datetime import datetime, timezone
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
)

from database import (
    get_all_incidents,
    get_all_tickets,
    get_database_stats,
    get_default_db_path,
    get_handover_report_by_id,
    get_handover_reports,
    init_db,
    save_handover_report,
    seed_data_from_json,
)
from fetch_activity import (
    fetch_activities,
    get_source_status,
    parse_and_normalize_timestamp,
)
from generator import generate_dummy_handover, generate_handover
from publisher import build_pdf_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_output_dir() -> str:
    """Returns a safe, writable output directory for PDF generation."""
    env_dir = os.getenv("OUTPUT_DIR")
    if env_dir:
        return env_dir
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        tmp_dir = "/tmp/output"
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except OSError:
            pass
        return tmp_dir
    try:
        local_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(local_dir, exist_ok=True)
        test_file = os.path.join(local_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return local_dir
    except (OSError, IOError, PermissionError):
        tmp_dir = "/tmp/output"
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except OSError:
            pass
        return tmp_dir


app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)
app.secret_key = os.getenv("SECRET_KEY", "shift-handover-secure-secret-key-2026")


# Enable CORS for Flutter Web / Mobile clients
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/api/generate", methods=["OPTIONS"])
@app.route("/api/login", methods=["OPTIONS"])
@app.route("/api/logout", methods=["OPTIONS"])
@app.route("/api/me", methods=["OPTIONS"])
@app.route("/api/reports", methods=["OPTIONS"])
@app.route("/api/data/tickets", methods=["OPTIONS"])
@app.route("/api/data/incidents", methods=["OPTIONS"])
def api_options():
    return jsonify({"status": "ok"}), 200


# Mock User Accounts for NOC & On-Call Teams
DEMO_USERS = {
    "operator@noc.internal": {
        "email": "operator@noc.internal",
        "name": "Alex Rivera",
        "role": "Lead On-Call SRE",
        "team": "Core Platform NOC",
        "badge": "L3 Operations",
        "avatar": "AR"
    },
    "supervisor@noc.internal": {
        "email": "supervisor@noc.internal",
        "name": "Maria Garcia",
        "role": "Shift Operations Supervisor",
        "team": "Global Incident Command",
        "badge": "Incident Commander",
        "avatar": "MG"
    },
    "admin@shifthandover.io": {
        "email": "admin@shifthandover.io",
        "name": "Admin Engineer",
        "role": "System Administrator",
        "team": "Infrastructure & Mesh",
        "badge": "Root Admin",
        "avatar": "AD"
    }
}

# Configuration
TICKETS_PATH = os.getenv("TICKETS_DATA_PATH", os.path.join(BASE_DIR, "data", "tickets.json"))
INCIDENTS_PATH = os.getenv("INCIDENTS_DATA_PATH", os.path.join(BASE_DIR, "data", "incidents.json"))
OUTPUT_DIR = get_output_dir()
DB_PATH = get_default_db_path()

# Initialize database & seed initial records
try:
    init_db(DB_PATH)
    seed_data_from_json(TICKETS_PATH, INCIDENTS_PATH, db_path=DB_PATH)
    logger.info("Database initialized and seeded successfully.")
except Exception as err:
    logger.error(f"Database initialization error: {err}")


@app.route("/login")
@app.route("/api/index/login")
@app.route("/api/index.py/login")
def login_page():
    """Renders the NOC Login Page."""
    try:
        return render_template("login.html")
    except Exception as e:
        logger.error(f"Error rendering login page: {e}")
        return jsonify({"error": "Unable to render login page"}), 500


@app.route("/api/login", methods=["POST"])
@app.route("/api/index/api/login", methods=["POST"])
@app.route("/api/index.py/api/login", methods=["POST"])
def api_login():
    """
    Authenticates operator with email & password (or demo login).
    """
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()

        if not email:
            return jsonify({"success": False, "error": "Email is required."}), 400

        user = DEMO_USERS.get(email, {
            "email": email,
            "name": email.split("@")[0].replace(".", " ").title(),
            "role": "On-Call Engineer",
            "team": "NOC Operations",
            "badge": "Active On-Call",
            "avatar": (email[:2]).upper()
        })

        return jsonify({
            "success": True,
            "message": "Authentication successful.",
            "user": user,
            "token": f"noc-token-{int(datetime.now().timestamp())}"
        })
    except Exception as e:
        logger.error(f"API login error: {e}")
        return jsonify({"success": False, "error": "Authentication service error."}), 500


@app.route("/api/me", methods=["GET"])
@app.route("/api/index/api/me", methods=["GET"])
@app.route("/api/index.py/api/me", methods=["GET"])
def api_me():
    """Returns currently authenticated operator profile."""
    try:
        return jsonify({
            "authenticated": True,
            "user": DEMO_USERS["operator@noc.internal"]
        })
    except Exception as e:
        logger.error(f"API me error: {e}")
        return jsonify({"authenticated": False, "error": "Internal server error"}), 500


@app.route("/api/logout", methods=["POST"])
@app.route("/api/index/api/logout", methods=["POST"])
@app.route("/api/index.py/api/logout", methods=["POST"])
def api_logout():
    """Logs out current operator."""
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/")
@app.route("/api/index")
@app.route("/api/index.py")
def index():
    """Renders the main Shift Handover Web Dashboard."""
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return jsonify({"error": "Unable to render dashboard"}), 500


@app.route("/api/debug-env", methods=["GET"])
@app.route("/api/index/api/debug-env", methods=["GET"])
@app.route("/api/index.py/api/debug-env", methods=["GET"])
def api_debug_env():
    """Diagnostic endpoint to inspect request headers and environ for serverless troubleshooting."""
    safe_environ = {}
    for k, v in request.environ.items():
        if isinstance(v, (str, int, float, bool, list, dict)):
            safe_environ[k] = v
        else:
            safe_environ[k] = str(type(v))
    return jsonify({
        "path": request.path,
        "method": request.method,
        "headers": dict(request.headers),
        "environ": safe_environ
    })


@app.route("/api/status", methods=["GET"])
@app.route("/api/index/api/status", methods=["GET"])
@app.route("/api/index.py/api/status", methods=["GET"])
def api_status():
    """Returns connected data sources health, PostgreSQL / SQLite database info and record counts."""
    try:
        tickets_status = get_source_status(TICKETS_PATH, "Ticketing")
        incidents_status = get_source_status(INCIDENTS_PATH, "Incident Management")
        db_stats = get_database_stats(DB_PATH)

        all_connected = tickets_status.get("connected", False) and incidents_status.get("connected", False) and db_stats.get("connected", False)
        
        return jsonify({
            "status": "READY" if all_connected else "DEGRADED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": db_stats,
            "sources": [tickets_status, incidents_status]
        })
    except Exception as e:
        logger.error(f"Error in api_status: {e}")
        return jsonify({
            "status": "DEGRADED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": "Failed to retrieve system status",
            "sources": []
        }), 500


@app.route("/api/data/tickets", methods=["GET"])
@app.route("/api/index/api/data/tickets", methods=["GET"])
@app.route("/api/index.py/api/data/tickets", methods=["GET"])
def api_data_tickets():
    """Returns all ticket records stored in database."""
    try:
        tickets = get_all_tickets(DB_PATH)
        return jsonify({"success": True, "count": len(tickets), "tickets": tickets})
    except Exception as e:
        logger.error(f"Error in api_data_tickets: {e}")
        return jsonify({"success": False, "error": "Failed to fetch tickets"}), 500


@app.route("/api/data/incidents", methods=["GET"])
@app.route("/api/index/api/data/incidents", methods=["GET"])
@app.route("/api/index.py/api/data/incidents", methods=["GET"])
def api_data_incidents():
    """Returns all incident records stored in database."""
    try:
        incidents = get_all_incidents(DB_PATH)
        return jsonify({"success": True, "count": len(incidents), "incidents": incidents})
    except Exception as e:
        logger.error(f"Error in api_data_incidents: {e}")
        return jsonify({"success": False, "error": "Failed to fetch incidents"}), 500


@app.route("/api/reports", methods=["GET"])
@app.route("/api/index/api/reports", methods=["GET"])
@app.route("/api/index.py/api/reports", methods=["GET"])
def api_reports_list():
    """Returns historical generated handover reports from database."""
    try:
        reports = get_handover_reports(limit=100, db_path=DB_PATH)
        return jsonify({"success": True, "count": len(reports), "reports": reports})
    except Exception as e:
        logger.error(f"Error in api_reports_list: {e}")
        return jsonify({"success": False, "error": "Failed to fetch reports"}), 500


@app.route("/api/reports/<int:report_id>", methods=["GET"])
@app.route("/api/index/api/reports/<int:report_id>", methods=["GET"])
@app.route("/api/index.py/api/reports/<int:report_id>", methods=["GET"])
def api_report_detail(report_id):
    """Returns full details and classified items of a specific handover report."""
    try:
        report = get_handover_report_by_id(report_id, db_path=DB_PATH)
        if not report:
            return jsonify({"success": False, "error": f"Report #{report_id} not found."}), 404
        return jsonify({"success": True, "report": report})
    except Exception as e:
        logger.error(f"Error in api_report_detail: {e}")
        return jsonify({"success": False, "error": "Failed to fetch report details"}), 500


@app.route("/api/generate", methods=["POST"])
@app.route("/api/index/api/generate", methods=["POST"])
@app.route("/api/index.py/api/generate", methods=["POST"])
def api_generate():
    """
    Main Generation API:
    Accepts:
    {
        "shift_start": "2026-09-03T17:00:00+05:30",
        "shift_end": "2026-09-03T20:00:00+05:30"
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        start_str = data.get("shift_start")
        end_str = data.get("shift_end")
        dummy_mode = data.get("dummy", False)

        # 1. Validation
        if not start_str or not end_str:
            return jsonify({
                "success": False,
                "error": "Both 'shift_start' and 'shift_end' are required ISO timestamps."
            }), 400

        start_dt = parse_and_normalize_timestamp(start_str)
        end_dt = parse_and_normalize_timestamp(end_str)

        if not start_dt:
            return jsonify({
                "success": False,
                "error": f"Invalid 'shift_start' timestamp format: '{start_str}'"
            }), 400

        if not end_dt:
            return jsonify({
                "success": False,
                "error": f"Invalid 'shift_end' timestamp format: '{end_str}'"
            }), 400

        if start_dt >= end_dt:
            return jsonify({
                "success": False,
                "error": f"Shift start ({start_dt.isoformat()}) must be strictly earlier than shift end ({end_dt.isoformat()})."
            }), 400

        start_utc = start_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        end_utc = end_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        # 2. Ingestion & Pipeline from PostgreSQL / SQLite
        if dummy_mode:
            sections = generate_dummy_handover()
            total_raw = 3
        else:
            sources = [
                {"path": TICKETS_PATH, "name": "Ticketing"},
                {"path": INCIDENTS_PATH, "name": "Incident"}
            ]
            raw_events = fetch_activities(sources, start_dt, end_dt, use_db=True, db_path=DB_PATH)
            total_raw = len(raw_events)
            sections = generate_handover(raw_events)

        # 3. PDF Generation
        filename_start = start_dt.strftime("%Y%m%d_%H%M%S")
        filename_end = end_dt.strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"handover_note_{filename_start}_to_{filename_end}.pdf"
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

        shift_meta = {
            "shift_start": f"{start_str} ({start_utc})",
            "shift_end": f"{end_str} ({end_utc})",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_items": total_raw
        }

        final_pdf_path = build_pdf_document(sections, pdf_path, shift_meta)
        actual_filename = os.path.basename(final_pdf_path)

        completed_items = sections.get("COMPLETED", [])
        in_progress_items = sections.get("IN PROGRESS", [])
        blockers_items = sections.get("BLOCKERS / ESCALATIONS", [])
        watch_list_items = sections.get("WATCH-LIST", [])

        total_collapsed = len(completed_items) + len(in_progress_items) + len(blockers_items) + len(watch_list_items)

        # 4. Save into Database
        report_id = None
        try:
            report_id = save_handover_report(
                shift_start=start_str,
                shift_end=end_str,
                generated_at=shift_meta["generated_at"],
                total_items=total_raw,
                completed_count=len(completed_items),
                in_progress_count=len(in_progress_items),
                blockers_count=len(blockers_items),
                watchlist_count=len(watch_list_items),
                pdf_filename=actual_filename,
                pdf_path=final_pdf_path,
                sections=sections,
                db_path=DB_PATH
            )
            logger.info(f"Handover report stored in database with ID #{report_id}")
        except Exception as db_e:
            logger.warning(f"Could not persist report to database: {db_e}")

        return jsonify({
            "success": True,
            "message": "Handover note generated successfully.",
            "report_id": report_id,
            "pdf_url": f"/api/download/{actual_filename}",
            "pdf_filename": actual_filename,
            "metrics": {
                "total_raw_events": total_raw,
                "total_collapsed_items": total_collapsed,
                "completed": len(completed_items),
                "in_progress": len(in_progress_items),
                "blockers": len(blockers_items),
                "watch_list": len(watch_list_items)
            },
            "shift_window": {
                "start": start_str,
                "end": end_str,
                "start_utc": start_utc,
                "end_utc": end_utc
            },
            "sections": {
                "completed": completed_items,
                "in_progress": in_progress_items,
                "blockers": blockers_items,
                "watch_list": watch_list_items
            }
        })

    except Exception as e:
        logger.exception(f"Error during handover generation: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to generate handover report: {str(e)}"
        }), 500


@app.route("/api/download/<filename>", methods=["GET"])
@app.route("/api/pdf/<filename>", methods=["GET"])
@app.route("/output/<filename>", methods=["GET"])
@app.route("/api/index/api/download/<filename>", methods=["GET"])
@app.route("/api/index.py/api/download/<filename>", methods=["GET"])
def download_pdf(filename):
    """
    Serves generated PDF for in-browser preview or attachment download.
    Properly sets Content-Type: application/pdf and Content-Disposition.
    """
    safe_filename = os.path.basename(filename)
    candidates = [
        os.path.join(OUTPUT_DIR, safe_filename),
        os.path.join("/tmp/output", safe_filename),
        os.path.join("/tmp", safe_filename),
        os.path.join(os.path.join(BASE_DIR, "output"), safe_filename)
    ]
    file_path = None
    for cand in candidates:
        if os.path.exists(cand):
            file_path = os.path.abspath(cand)
            break
    
    if not file_path:
        return jsonify({
            "success": False,
            "error": f"Report file '{safe_filename}' not found."
        }), 404

    is_download = request.args.get("download", "").lower() in ["1", "true", "yes"]
    disposition = f'attachment; filename="{safe_filename}"' if is_download else f'inline; filename="{safe_filename}"'
        
    try:
        response = send_file(
            file_path,
            mimetype="application/pdf",
            as_attachment=is_download,
            download_name=safe_filename
        )
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = disposition
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as err:
        logger.error(f"Failed to send PDF file '{file_path}': {err}")
        return jsonify({"success": False, "error": f"Error serving PDF: {str(err)}"}), 500


@app.route("/static/<path:filename>", methods=["GET"])
@app.route("/api/index/static/<path:filename>", methods=["GET"])
@app.route("/api/index.py/static/<path:filename>", methods=["GET"])
def serve_static(filename):
    """Explicit static asset server with correct MIME types."""
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5050))
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    print(f"⚡ SHIFT//HANDOVER Web Dashboard running at http://localhost:{port}")
    app.run(host=host, port=port, debug=False)
