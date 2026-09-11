import os
import sys

# Ensure root directory is on Python path for Vercel Serverless Function
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app


class VercelPathFixMiddleware:
    """
    WSGI Middleware to normalize PATH_INFO in Vercel Serverless Functions.
    Handles Vercel rewrites, preserving actual user request routes.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get("PATH_INFO", "")
        raw_uri = (
            environ.get("HTTP_X_MATCHED_PATH")
            or environ.get("HTTP_X_FORWARDED_URI")
            or environ.get("HTTP_X_REAL_URL")
            or environ.get("RAW_URI")
            or environ.get("REQUEST_URI")
        )

        # Handle exact match on Vercel function endpoints
        if path_info in ("/api/index.py", "/api/index", "/api", "/api/"):
            if raw_uri:
                clean_raw = raw_uri.split("?")[0]
                if clean_raw and clean_raw not in ("/api/index.py", "/api/index", "/api", "/api/"):
                    environ["PATH_INFO"] = clean_raw
                else:
                    environ["PATH_INFO"] = "/"
            else:
                environ["PATH_INFO"] = "/"
        elif path_info.startswith("/api/index.py/"):
            environ["PATH_INFO"] = path_info[len("/api/index.py"):]
        elif path_info.startswith("/api/index/"):
            environ["PATH_INFO"] = path_info[len("/api/index"):]

        if not environ.get("PATH_INFO"):
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


# Apply middleware to Flask WSGI app
app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)
