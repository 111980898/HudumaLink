"""
Security helpers: CSRF protection, access-control decorators, login throttling
and upload validation. Kept separate so the rules are easy to audit.
"""
import secrets
import time
from functools import wraps

from flask import abort, current_app, flash, redirect, request, session, url_for

from .constants import IMAGE_SIGNATURES


# --- CSRF -------------------------------------------------------------------
def csrf_token() -> str:
    """Return (creating if needed) the token embedded in every HTML form."""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def verify_csrf() -> None:
    """Abort with 400 if a POST request lacks a matching CSRF token."""
    sent = request.form.get("csrf_token", "")
    expected = session.get("_csrf", "")
    if not sent or not expected or not secrets.compare_digest(sent, expected):
        abort(400, description="Your form session expired. Please go back, reload the page and try again.")


# --- Access control ---------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def safe_next_url(target: str, fallback: str) -> str:
    """Only follow ``?next=`` if it is a local path (prevents open redirects)."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return fallback


# --- Login throttling -------------------------------------------------------
# In-memory is fine for a single-process demo; a real deployment would use Redis.
_failures: dict[str, list[float]] = {}


def _key(email: str) -> str:
    return f"{email}|{request.remote_addr}"


def too_many_attempts(email: str) -> bool:
    window = current_app.config["LOGIN_WINDOW_SECONDS"]
    recent = [t for t in _failures.get(_key(email), []) if time.time() - t < window]
    _failures[_key(email)] = recent
    return len(recent) >= current_app.config["LOGIN_MAX_ATTEMPTS"]


def record_failure(email: str) -> None:
    _failures.setdefault(_key(email), []).append(time.time())


def clear_failures(email: str) -> None:
    _failures.pop(_key(email), None)


# --- Upload validation ------------------------------------------------------
def looks_like_image(file_storage, ext: str) -> bool:
    """
    Check the file's real first bytes, not just its name. A renamed .exe or
    .html file will fail here even if it is called "photo.png".
    """
    head = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    signatures = IMAGE_SIGNATURES.get(ext, ())
    if not any(head.startswith(sig) for sig in signatures):
        return False
    if ext == "webp":                       # RIFF container must say WEBP
        return head[8:12] == b"WEBP"
    return True
