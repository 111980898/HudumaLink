"""
Security helpers for Huduma Link.

The login limiter is stored in the application database rather than process
memory so it remains effective when Vercel routes requests to new instances.
"""

import hashlib
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
        abort(
            400,
            description="Your form session expired. Please go back, reload the page and try again.",
        )


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
def _bucket(value: str) -> str:
    """Hash the limiter key so email/IP values are not stored in plain text."""
    secret = current_app.config["SECRET_KEY"]
    return hashlib.sha256(f"{secret}|{value}".encode()).hexdigest()


def _keys(email: str) -> tuple[str, str]:
    normalized_email = email.strip().lower()[:254]
    remote_addr = (request.remote_addr or "unknown")[:128]
    # Check both identity+address and address-wide buckets. This prevents an
    # attacker from bypassing limits simply by trying many email addresses.
    return _bucket(f"email:{normalized_email}|ip:{remote_addr}"), _bucket(f"ip:{remote_addr}")


def _recent_attempts(bucket: str) -> int:
    from .db import get_db

    row = (
        get_db()
        .execute("SELECT attempts, first_at FROM login_attempts WHERE bucket = ?", (bucket,))
        .fetchone()
    )
    if not row:
        return 0
    now = time.time()
    if now - float(row["first_at"]) >= current_app.config["LOGIN_WINDOW_SECONDS"]:
        get_db().execute("DELETE FROM login_attempts WHERE bucket = ?", (bucket,))
        get_db().commit()
        return 0
    return int(row["attempts"])


def too_many_attempts(email: str) -> bool:
    return any(
        _recent_attempts(bucket) >= current_app.config["LOGIN_MAX_ATTEMPTS"]
        for bucket in _keys(email)
    )


def record_failure(email: str) -> None:
    from .db import get_db

    now = time.time()
    db = get_db()
    for bucket in _keys(email):
        db.execute(
            "INSERT INTO login_attempts (bucket, attempts, first_at, last_at) VALUES (?, 1, ?, ?) "
            "ON CONFLICT(bucket) DO UPDATE SET attempts = login_attempts.attempts + 1, "
            "last_at = excluded.last_at",
            (bucket, now, now),
        )
    db.commit()


def clear_failures(email: str) -> None:
    from .db import get_db

    db = get_db()
    for bucket in _keys(email):
        db.execute("DELETE FROM login_attempts WHERE bucket = ?", (bucket,))
    db.commit()


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
    if ext == "webp":  # RIFF container must say WEBP
        return head[8:12] == b"WEBP"
    return True
