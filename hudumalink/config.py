"""Environment-driven configuration for HudumaLink."""
import os
import tempfile

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ON_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
WRITABLE_ROOT = tempfile.gettempdir() if ON_SERVERLESS else os.path.join(BASE_DIR, "instance")


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-secret-change-me"
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(WRITABLE_ROOT, "hudumalink.db")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or os.path.join(WRITABLE_ROOT, "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    PER_PAGE = 10
    SESSION_COOKIE_HTTPONLY = True
    # Preview is embedded cross-site over HTTPS. Local HTTP can set this to false.
    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
    # Keep the assessment/Preview experience populated. Set DEMO_MODE=0 for a clean deployment.
    DEMO_MODE = env_bool("DEMO_MODE", True)
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW_SECONDS = 300
