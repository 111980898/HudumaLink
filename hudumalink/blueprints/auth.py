"""Registration, sign-in and sign-out."""

import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .. import security
from ..constants import SUB_COUNTIES
from ..db import DB_INTEGRITY_ERRORS, get_db, utcnow

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_password(password: str) -> str | None:
    """Return an error message if the password is too weak, else None."""
    if len(password) < 8:
        return "Use a password with at least 8 characters."
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        return "Your password must contain both letters and numbers."
    return None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = {
            k: request.form.get(k, "").strip()[:254]
            for k in ("full_name", "email", "phone", "sub_county")
        }
        form["full_name"] = form["full_name"][:120]
        form["phone"] = form["phone"][:20]
        form["email"] = form["email"].lower()
        password = request.form.get("password", "")

        error = None
        if len(form["full_name"]) < 3:
            error = "Please enter your full name."
        elif not EMAIL_RE.match(form["email"]):
            error = "Please enter a valid email address."
        elif form["sub_county"] not in SUB_COUNTIES:
            error = "Please choose your sub-county."
        elif form["phone"] and not re.fullmatch(r"(\+254|0)\d{9}", form["phone"].replace(" ", "")):
            error = "Phone numbers look like 0712345678 or +254712345678."
        elif len(password) > 256:
            error = "Use a password of 256 characters or fewer."
        else:
            error = validate_password(password)

        if error:
            flash(error, "error")
            return render_template("auth/register.html", form=form), 400

        try:
            db = get_db()
            # Public sign-up ALWAYS creates a citizen. Administrators are
            # created by the system owner (see README), never by the public.
            db.execute(
                "INSERT INTO users (full_name, email, phone, sub_county, password_hash, "
                "role, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'citizen', ?)",
                (
                    form["full_name"],
                    form["email"],
                    form["phone"],
                    form["sub_county"],
                    generate_password_hash(password),
                    utcnow(),
                ),
            )
            db.commit()
        except DB_INTEGRITY_ERRORS:
            flash("An account with that email already exists. Try signing in.", "error")
            return render_template("auth/register.html", form=form), 409

        flash("Your account is ready. Please sign in.", "success")
        return redirect(url_for("auth.login", registered="1"))
    return render_template("auth/register.html", form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    registered = request.args.get("registered") == "1"
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")[:256]
        account_type = request.form.get("account_type", "citizen").strip().lower()
        if account_type not in {"citizen", "admin"}:
            account_type = "citizen"

        if security.too_many_attempts(email):
            flash("Too many failed attempts. Please wait a few minutes and try again.", "error")
            return (
                render_template(
                    "auth/login.html", selected_role=account_type, registered=registered
                ),
                429,
            )

        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if (
            user
            and user["role"] == account_type
            and check_password_hash(user["password_hash"], password)
        ):
            security.clear_failures(email)
            session.clear()  # new session = no fixation
            session.update(user_id=user["id"], name=user["full_name"], role=user["role"])
            flash(f"Welcome back, {user['full_name'].split()[0]}.", "success")
            home = url_for("admin.dashboard" if user["role"] == "admin" else "citizen.dashboard")
            return redirect(security.safe_next_url(request.args.get("next", ""), home))

        security.record_failure(email)
        # Keep the failure response generic so attackers cannot enumerate
        # registered emails or account roles.
        flash("That email, password, or workspace selection is not valid.", "error")
        return (
            render_template("auth/login.html", selected_role=account_type, registered=registered),
            401,
        )
    return render_template("auth/login.html", selected_role="citizen", registered=registered)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("public.home"))
