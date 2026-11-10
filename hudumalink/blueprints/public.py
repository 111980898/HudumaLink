"""Pages anyone can open without signing in."""
from flask import Blueprint, abort, current_app, jsonify, render_template, request, send_from_directory

from .. import services
from ..constants import CATEGORIES
from ..db import get_db

bp = Blueprint("public", __name__)


@bp.route("/")
def home():
    db = get_db()
    recent = db.execute(
        "SELECT reference, category, subject, sub_county, status, updated_at FROM service_requests "
        "ORDER BY updated_at DESC LIMIT 5").fetchall()
    return render_template("public/home.html", stats=services.public_stats(db), recent=recent,
                           satisfaction=services.satisfaction(db))


@bp.route("/track", methods=["GET"])
def track():
    """Anyone with a reference number can check progress — no account needed."""
    reference = request.args.get("ref", "").strip().upper()
    item = history = None
    if reference:
        db = get_db()
        item = db.execute("SELECT * FROM service_requests WHERE reference = ?", (reference,)).fetchone()
        if item:
            history = db.execute(
                "SELECT * FROM status_history WHERE request_id = ? ORDER BY id", (item["id"],)).fetchall()
    return render_template("public/track.html", reference=reference, item=item, history=history)


@bp.route("/services")
def services_page():
    query = request.args.get("q", "").strip()[:80]
    items = list(CATEGORIES.items())
    if query:
        needle = query.lower()
        items = [(name, info) for name, info in items
                 if needle in name.lower() or needle in info["department"].lower()]
    return render_template("public/services.html", query=query, service_items=items)


@bp.route("/faq")
def faq():
    return render_template("public/faq.html")


@bp.route("/media/<path:filename>")
def media(filename):
    """Serve uploaded photos from the (possibly non-static) upload folder."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.route("/manus-routes.json")
def route_manifest():
    """Serve the managed Preview route declaration from the application root."""
    return send_from_directory(current_app.static_folder or "", "manus-routes.json")


@bp.route("/_app/health")
def health():
    """Unauthenticated readiness response used by the published container."""
    return jsonify(status="ok", service="huduma-link"), 200
