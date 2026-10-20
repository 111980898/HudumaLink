"""Everything a signed-in citizen does: file requests, follow progress, give feedback."""
import os
import secrets

from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from .. import security, services
from ..constants import CATEGORIES, IMAGE_SIGNATURES, PRIORITIES, SUB_COUNTIES
from ..db import get_db
from .auth import validate_password

bp = Blueprint("citizen", __name__)


def current_user():
    return get_db().execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()


@bp.route("/dashboard")
@security.login_required
def dashboard():
    if session["role"] == "admin":
        return redirect(url_for("admin.dashboard"))
    db = get_db()
    status = request.args.get("status", "")
    sql, args = "SELECT * FROM service_requests WHERE user_id = ?", [session["user_id"]]
    if status:
        sql += " AND status = ?"
        args.append(status)
    rows = db.execute(sql + " ORDER BY id DESC", args).fetchall()
    notes = db.execute(
        "SELECT n.*, r.reference FROM notifications n JOIN service_requests r ON r.id = n.request_id "
        "WHERE n.user_id = ? ORDER BY n.id DESC LIMIT 8", (session["user_id"],)).fetchall()
    return render_template("citizen/dashboard.html", requests=rows, notifications=notes,
                           stats=services.overall_stats(db, session["user_id"]), active=status)


@bp.route("/requests/new", methods=["GET", "POST"])
@security.login_required
def new_request():
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip()
                for k in ("category", "subject", "description", "location", "sub_county", "priority")}
        problems = []
        if form["category"] not in CATEGORIES:
            problems.append("Choose a service category.")
        if form["sub_county"] not in SUB_COUNTIES:
            problems.append("Choose the sub-county where the problem is.")
        if form["priority"] not in PRIORITIES:
            form["priority"] = "Normal"
        if not 5 <= len(form["subject"]) <= 100:
            problems.append("The title must be between 5 and 100 characters.")
        if not 15 <= len(form["description"]) <= 1500:
            problems.append("Describe the problem in 15–1500 characters so the team can act on it.")
        if len(form["location"]) < 3:
            problems.append("Tell us where the problem is (a landmark or street is fine).")

        image_name = ""
        upload = request.files.get("image")
        if upload and upload.filename:
            ext = secure_filename(upload.filename).rsplit(".", 1)[-1].lower()
            if ext not in IMAGE_SIGNATURES or not security.looks_like_image(upload, ext):
                problems.append("The photo must be a real PNG, JPG, GIF or WEBP image.")
            else:
                image_name = f"{secrets.token_hex(12)}.{ext}"

        if problems:
            for p in problems:
                flash(p, "error")
            return render_template("citizen/new_request.html", form=form), 400

        if image_name:
            upload.save(os.path.join(current_app.config["UPLOAD_FOLDER"], image_name))
        db = get_db()
        reference = services.create_request(db, current_user(), form, image_name)
        db.commit()
        flash(f"Request submitted. Your tracking number is {reference}.", "success")
        return redirect(url_for("citizen.dashboard"))
    return render_template("citizen/new_request.html", form={})


@bp.route("/requests/<int:request_id>")
@security.login_required
def detail(request_id):
    db = get_db()
    item = db.execute(
        "SELECT r.*, u.full_name, u.email, u.phone FROM service_requests r "
        "JOIN users u ON u.id = r.user_id WHERE r.id = ?", (request_id,)).fetchone()
    if not item:
        abort(404)
    if session["role"] != "admin" and item["user_id"] != session["user_id"]:
        abort(403)                      # citizens may only see their own requests
    history = db.execute(
        "SELECT * FROM status_history WHERE request_id = ? ORDER BY id DESC", (request_id,)).fetchall()
    return render_template("citizen/detail.html", item=item, history=history)


@bp.route("/requests/<int:request_id>/feedback", methods=["POST"])
@security.login_required
def feedback(request_id):
    """Let a citizen rate the service once their request is resolved."""
    db = get_db()
    item = db.execute("SELECT * FROM service_requests WHERE id = ? AND user_id = ?",
                      (request_id, session["user_id"])).fetchone()
    if not item:
        abort(404)
    rating = request.form.get("rating", type=int)
    if item["status"] != "Resolved" or rating not in range(1, 6):
        flash("You can rate a request once it is resolved, from 1 to 5 stars.", "error")
    else:
        db.execute("UPDATE service_requests SET rating = ?, feedback = ? WHERE id = ?",
                   (rating, request.form.get("feedback", "").strip()[:300], request_id))
        db.commit()
        flash("Thank you — your feedback helps improve county services.", "success")
    return redirect(url_for("citizen.detail", request_id=request_id))


@bp.route("/notifications/read", methods=["POST"])
@security.login_required
def read_notifications():
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (session["user_id"],))
    db.commit()
    return redirect(request.referrer or url_for("citizen.dashboard"))


@bp.route("/profile", methods=["GET", "POST"])
@security.login_required
def profile():
    db, user = get_db(), current_user()
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        error = validate_password(new_pw)
        if not check_password_hash(user["password_hash"], current_pw):
            error = "Your current password is not correct."
        if error:
            flash(error, "error")
        else:
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                       (generate_password_hash(new_pw), user["id"]))
            db.commit()
            flash("Password updated.", "success")
            return redirect(url_for("citizen.profile"))
    return render_template("citizen/profile.html", user=user,
                           stats=services.overall_stats(db, user["id"]))
