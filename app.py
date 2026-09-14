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

import json
import logging
import os
import sys
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Optional

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

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


DEFAULT_SECRET_KEY = "shift-handover-secure-secret-key-2026"

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)
app.secret_key = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)

# Startup warning if using default SECRET_KEY in non-debug mode
if not app.debug and app.secret_key == DEFAULT_SECRET_KEY:
    logger.warning(
        "SECURITY WARNING: Running in a non-debug environment with the default SECRET_KEY! "
        "Please set a secure SECRET_KEY environment variable in production."
    )

serializer = URLSafeTimedSerializer(app.secret_key, salt="shift-auth-token")


# Enable CORS for Flutter Web / Mobile clients
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Auth-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/api/generate", methods=["OPTIONS"])
@app.route("/api/login", methods=["OPTIONS"])
@app.route("/api/logout", methods=["OPTIONS"])
@app.route("/api/me", methods=["OPTIONS"])
@app.route("/api/reports", methods=["OPTIONS"])
@app.route("/api/data/tickets", methods=["OPTIONS"])
@app.route("/api/data/incidents", methods=["OPTIONS"])
@app.route("/api/debug-env", methods=["OPTIONS"])
def api_options():
    return jsonify({"status": "ok"}), 200


# User Accounts for NOC & On-Call Teams
USERS_PATH = os.getenv("USERS_DATA_PATH", os.path.join(BASE_DIR, "data", "users.json"))

DEFAULT_DEMO_USERS: Dict[str, Dict[str, Any]] = {
    "operator@noc.internal": {
        "email": "operator@noc.internal",
        "password_hash": generate_password_hash("demo"),
        "name": "Alex Rivera",
        "role": "Lead On-Call SRE",
        "team": "Core Platform NOC",
        "badge": "L3 Operations",
        "avatar": "AR"
    },
    "supervisor@noc.internal": {
        "email": "supervisor@noc.internal",
        "password_hash": generate_password_hash("demo"),
        "name": "Maria Garcia",
        "role": "Shift Operations Supervisor",
        "team": "Global Incident Command",
        "badge": "Incident Commander",
        "avatar": "MG"
    },
    "admin@shifthandover.io": {
        "email": "admin@shifthandover.io",
        "password_hash": generate_password_hash("demo"),
        "name": "Admin Engineer",
        "role": "System Administrator",
        "team": "Infrastructure & Mesh",
        "badge": "Root Admin",
        "avatar": "AD"
    }
}


def verify_user_password(user: Optional[Dict[str, Any]], password: Optional[str]) -> bool:
    """Safely verifies a user password against password_hash with fallback."""
    if not user or not password:
        return False
    pw_hash = user.get("password_hash")
    if pw_hash:
        try:
            if check_password_hash(str(pw_hash), str(password)):
                return True
        except Exception as e:
            logger.warning(f"check_password_hash verification warning: {e}")
    # Safe fallback for seeded demo accounts
    if str(password) == "demo" and user.get("email") in DEFAULT_DEMO_USERS:
        return True
    return False


def load_users() -> Dict[str, Dict[str, Any]]:
    """Loads users from users.json seed or falls back to DEFAULT_DEMO_USERS."""
    users = {}
    # First populate with DEFAULT_DEMO_USERS
    for em, u in DEFAULT_DEMO_USERS.items():
        users[em.lower()] = dict(u)

    if os.path.exists(USERS_PATH):
        try:
            with open(USERS_PATH, "r", encoding="utf-8") as f:
                user_list = json.load(f)
                for u in user_list:
                    email = (u.get("email") or "").strip().lower()
                    if not email:
                        continue
                    if "password_hash" not in u and "password" in u:
                        u["password_hash"] = generate_password_hash(u["password"])
                    elif "password_hash" not in u:
                        u["password_hash"] = generate_password_hash("demo")
                    users[email] = u
        except Exception as e:
            logger.warning(f"Failed to load users from {USERS_PATH}: {e}")

    return users


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Looks up user by email (case-insensitive)."""
    if not email:
        return None
    users = load_users()
    return users.get(email.strip().lower())


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Extracts and validates token from Authorization header, X-Auth-Token, or session.
    Returns user dict if valid and unexpired, None otherwise.
    """
    token = None

    # 1. Check Authorization header (Bearer <token> or <token>)
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header:
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        else:
            token = auth_header

    # 2. Check X-Auth-Token header
    if not token:
        token = request.headers.get("X-Auth-Token", "").strip()

    # 3. Check Flask session
    if not token:
        try:
            token = session.get("token")
        except Exception:
            token = None

    if token:
        try:
            # 24 hour token validity = 86400 seconds
            payload = serializer.loads(token, max_age=86400)
            email = (payload.get("email") or "").strip().lower()
            if email:
                user = get_user_by_email(email)
                if user:
                    return user
            return None
        except (SignatureExpired, BadSignature, Exception):
            return None

    # Fallback: check session user_email if session token was not explicitly set
    try:
        session_email = session.get("user_email")
        if session_email:
            user = get_user_by_email(str(session_email).strip().lower())
            if user:
                return user
    except Exception:
        pass

    return None


def require_auth(f):
    """Decorator to require valid authentication token or session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                "success": False,
                "authenticated": False,
                "error": "Unauthorized: Authentication token is missing, invalid, or expired."
            }), 401
        return f(*args, **kwargs)
    return decorated


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
    Authenticates operator with email & password.
    Validates password hash, issues real signed token, sets session.
    """
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or request.form.get("email") or "").strip().lower()
        password = data.get("password") or request.form.get("password")

        if not email:
            return jsonify({"success": False, "error": "Email is required."}), 400

        if not password:
            return jsonify({"success": False, "error": "Password is required."}), 401

        user = get_user_by_email(email)
        if not user or not verify_user_password(user, password):
            return jsonify({"success": False, "error": "Invalid email or password."}), 401

        # Generate signed session token
        try:
            token = serializer.dumps({"email": user["email"]})
        except Exception:
            fallback_ser = URLSafeTimedSerializer(DEFAULT_SECRET_KEY, salt="shift-auth-token")
            token = fallback_ser.dumps({"email": user["email"]})

        # Store in session safely
        try:
            session["token"] = token
            session["user_email"] = user["email"]
        except Exception as sess_err:
            logger.warning(f"Could not set session variable: {sess_err}")

        # Safe user payload (exclude password_hash)
        safe_user = {k: v for k, v in user.items() if k != "password_hash"}

        return jsonify({
            "success": True,
            "message": "Authentication successful.",
            "user": safe_user,
            "token": token
        }), 200
    except Exception as e:
        logger.error(f"API login error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Authentication service error."}), 500


@app.route("/api/me", methods=["GET"])
@app.route("/api/index/api/me", methods=["GET"])
@app.route("/api/index.py/api/me", methods=["GET"])
def api_me():
    """Returns currently authenticated operator profile."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({
                "authenticated": False,
                "error": "Unauthorized: Authentication token is missing, invalid, or expired."
            }), 401

        safe_user = {k: v for k, v in user.items() if k != "password_hash"}
        return jsonify({
            "authenticated": True,
            "user": safe_user
        }), 200
    except Exception as e:
        logger.error(f"API me error: {e}")
        return jsonify({"authenticated": False, "error": "Internal server error"}), 500


@app.route("/api/logout", methods=["POST"])
@app.route("/api/index/api/logout", methods=["POST"])
@app.route("/api/index.py/api/logout", methods=["POST"])
def api_logout():
    """Logs out current operator and clears session."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/")
@app.route("/api/index")
@app.route("/api/index.py")
def index():
    """Renders the main Shift Handover Web Dashboard (guarded)."""
    user = get_current_user()
    if not user:
        return redirect("/login")
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return jsonify({"error": "Unable to render dashboard"}), 500


@app.route("/api/debug-env", methods=["GET"])
@app.route("/api/index/api/debug-env", methods=["GET"])
@app.route("/api/index.py/api/debug-env", methods=["GET"])
@require_auth
def api_debug_env():
    """Diagnostic endpoint to inspect request headers and environ for serverless troubleshooting (debug only)."""
    if not app.debug:
        return jsonify({"error": "Endpoint disabled in non-debug environment."}), 404

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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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

        # Total feed records across connected data sources
        total_source_records = 0
        try:
            total_source_records = len(get_all_tickets(DB_PATH)) + len(get_all_incidents(DB_PATH))
        except Exception:
            total_source_records = 0

        # 2. Ingestion & Pipeline from PostgreSQL / SQLite
        if dummy_mode:
            sections = generate_dummy_handover()
            total_raw = 3
            if total_source_records == 0:
                total_source_records = 3
        else:
            sources = [
                {"path": TICKETS_PATH, "name": "Ticketing"},
                {"path": INCIDENTS_PATH, "name": "Incident"}
            ]
            raw_events = fetch_activities(sources, start_dt, end_dt, use_db=True, db_path=DB_PATH)
            total_raw = len(raw_events)
            sections = generate_handover(raw_events)

        if total_source_records < total_raw:
            total_source_records = total_raw

        records_excluded = max(0, total_source_records - total_raw)

        completed_items = sections.get("COMPLETED", [])
        in_progress_items = sections.get("IN PROGRESS", [])
        blockers_items = sections.get("BLOCKERS / ESCALATIONS", [])
        watch_list_items = sections.get("WATCH-LIST", [])

        total_collapsed = len(completed_items) + len(in_progress_items) + len(blockers_items) + len(watch_list_items)

        # 3. PDF Generation
        filename_start = start_dt.strftime("%Y%m%d_%H%M%S")
        filename_end = end_dt.strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"handover_note_{filename_start}_to_{filename_end}.pdf"
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

        shift_meta = {
            "shift_start": f"{start_str} ({start_utc})",
            "shift_end": f"{end_str} ({end_utc})",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_items": total_source_records,
            "records_inside_shift": total_raw,
            "records_excluded": records_excluded,
            "unique_items_count": total_collapsed
        }

        final_pdf_path = build_pdf_document(sections, pdf_path, shift_meta)
        actual_filename = os.path.basename(final_pdf_path)

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
                "total_source_records": total_source_records,
                "total_raw_events": total_raw,
                "records_inside_shift": total_raw,
                "records_excluded": records_excluded,
                "unique_items_count": total_collapsed,
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
