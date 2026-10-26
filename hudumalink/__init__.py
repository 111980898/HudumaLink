"""HudumaLink application factory."""
import os

from flask import Flask, render_template, session

from . import db, security
from .config import Config
from .constants import CATEGORIES, PRIORITIES, STATUSES, SUB_COUNTIES


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if app.config.get("TESTING") and "SESSION_COOKIE_SECURE" not in (test_config or {}):
        app.config["SESSION_COOKIE_SECURE"] = False
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.init_db()

    app.jinja_env.globals["csrf_token"] = security.csrf_token

    @app.before_request
    def _csrf_guard():
        from flask import request
        if request.method == "POST":
            security.verify_csrf()

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
            row = db.get_db().execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
                (session["user_id"],),
            ).fetchone()
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
