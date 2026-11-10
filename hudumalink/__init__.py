"""HudumaLink application factory."""

import logging
import os

from flask import Flask, render_template, request, session

from . import db, security
from .config import Config
from .constants import CATEGORIES, PRIORITIES, STATUSES, SUB_COUNTIES

LOGGER = logging.getLogger(__name__)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.config["DEBUG"] = False
    if not app.config.get("TESTING") and not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be configured outside local testing")
    if app.config.get("TESTING") and "SESSION_COOKIE_SECURE" not in (test_config or {}):
        app.config["SESSION_COOKIE_SECURE"] = False
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    with app.app_context():
        try:
            db.init_db()
        except Exception:
            # Keep the process and /_app/health available when Neon is briefly
            # unavailable. /_app/ready reports the dependency failure clearly.
            app.config["DATABASE_INIT_ERROR"] = True
            LOGGER.exception("Huduma Link database initialization failed")
            if app.config.get("TESTING"):
                raise

    app.jinja_env.globals["csrf_token"] = security.csrf_token

    @app.before_request
    def _csrf_guard():
        from flask import request

        if request.method == "POST":
            security.verify_csrf()

    @app.after_request
    def _security_headers(response):
        """Apply baseline browser protections to every response."""
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(self)"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'self'; object-src 'none'; "
            "form-action 'self'; frame-ancestors https://*.manus.computer; "
            "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; "
            "connect-src 'self'",
        )
        private_paths = (
            "/login",
            "/register",
            "/admin",
            "/dashboard",
            "/requests",
            "/profile",
            "/notifications",
        )
        if session.get("user_id") or request.path.startswith(private_paths):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.jinja_env.globals.update(
        CATEGORIES=CATEGORIES,
        PRIORITIES=PRIORITIES,
        STATUSES=STATUSES,
        SUB_COUNTIES=SUB_COUNTIES,
    )
    from .filters import register_filters

    register_filters(app)

    @app.context_processor
    def _inject_unread():
        """Make the unread-notification count available to the navbar."""
        if session.get("user_id") and session.get("role") == "citizen":
            row = (
                db.get_db()
                .execute(
                    "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
                    (session["user_id"],),
                )
                .fetchone()
            )
            return {"unread_count": row[0]}
        return {"unread_count": 0}

    from .blueprints import admin, auth, citizen, public

    for blueprint in (public.bp, auth.bp, citizen.bp, admin.bp):
        app.register_blueprint(blueprint)

    messages = {
        400: "The request could not be processed.",
        403: "You do not have permission to view this page.",
        404: "We could not find the page or request you were looking for.",
        413: "That file is too large. Please upload an image smaller than 5 MB.",
    }
    for code, default in messages.items():

        def handler(error, code=code, default=default):
            text = getattr(error, "description", None)
            if code == 400 and text:
                default = text
            return render_template("error.html", code=code, message=default), code

        app.register_error_handler(code, handler)

    return app
