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
    Handles Vercel rewrites and routes, preserving actual user request routes.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get("PATH_INFO", "")

        # If PATH_INFO is prefixed by /api/index.py or /api/index, strip it
        if path_info.startswith("/api/index.py/"):
            environ["PATH_INFO"] = path_info[len("/api/index.py"):]
        elif path_info.startswith("/api/index/"):
            environ["PATH_INFO"] = path_info[len("/api/index"):]
        elif path_info in ("/api/index.py", "/api/index", "/api", "/api/"):
            # Check for actual request path in headers
            candidates = [
                environ.get("HTTP_X_VERCEL_PATH"),
                environ.get("HTTP_X_FORWARDED_PATH"),
                environ.get("HTTP_X_FORWARDED_URI"),
                environ.get("HTTP_X_REAL_URL"),
                environ.get("REQUEST_URI"),
                environ.get("RAW_URI"),
                environ.get("HTTP_X_MATCHED_PATH"),
            ]
            real_path = "/"
            for cand in candidates:
                if cand:
                    clean = cand.split("?")[0]
                    # Discard regex patterns or internal vercel endpoints
                    if (
                        clean
                        and not any(c in clean for c in "()[]*+?")
                        and clean not in ("/api/index.py", "/api/index", "/api", "/api/")
                    ):
                        real_path = clean
                        break
            environ["PATH_INFO"] = real_path

        if not environ.get("PATH_INFO"):
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


# Apply middleware to Flask WSGI app
app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)
