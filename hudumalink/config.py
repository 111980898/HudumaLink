"""
Configuration for HudumaLink.

Everything that changes between your laptop and a live deployment is read from
environment variables here, so no secret ever has to live in the source code.
"""
import os
import tempfile

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Vercel (and most serverless hosts) give you a read-only project folder, and
# only /tmp is writable. We detect that and store the database/uploads there.
ON_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
WRITABLE_ROOT = tempfile.gettempdir() if ON_SERVERLESS else os.path.join(BASE_DIR, "instance")


class Config:
    # Used to sign session cookies. SET THIS in production (see README).
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-secret-change-me"

    DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(WRITABLE_ROOT, "hudumalink.db")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or os.path.join(WRITABLE_ROOT, "uploads")

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024          # 5 MB upload ceiling
    PER_PAGE = 10                                 # rows per admin page

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = ON_SERVERLESS or os.environ.get("FLASK_ENV") == "production"

    # Optional first administrator, created at start-up if it does not exist.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

    # When true, the app seeds a demo admin, a demo citizen and sample requests
    # so a fresh install (or a serverless cold start) is never an empty page.
    DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() in {"1", "true", "yes"}

    # Login brute-force protection: N failures per window, per email + IP.
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW_SECONDS = 300
