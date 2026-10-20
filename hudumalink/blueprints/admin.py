"""Staff-only area: the case queue, analytics and data export."""
import csv
import io

from flask import (Blueprint, Response, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)

from .. import security, services
from ..constants import ALLOWED_TRANSITIONS, CATEGORIES, PRIORITIES, STATUSES, SUB_COUNTIES
from ..db import get_db

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _filters():
    """Read and sanitise the queue filters from the query string."""
    return {
        "status": request.args.get("status", "") if request.args.get("status") in STATUSES else "",
        "category": request.args.get("category", "") if request.args.get("category") in CATEGORIES else "",
        "sub_county": request.args.get("sub_county", "") if request.args.get("sub_county") in SUB_COUNTIES else "",
        "q": request.args.get("q", "").strip()[:100],
    }


def _where(f):
    """Build a parameterised WHERE clause from the filters (no string-pasting of user input)."""
    clauses, params = [], []
    for col, key in (("r.status", "status"), ("r.category", "category"), ("r.sub_county", "sub_county")):
        if f[key]:
            clauses.append(f"{col} = ?")
            params.append(f[key])
    if f["q"]:
        like = f"%{f['q']}%"
        clauses.append("(r.reference LIKE ? OR r.subject LIKE ? OR r.location LIKE ? OR u.full_name LIKE ? OR u.email LIKE ?)")
        params += [like] * 5
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


@bp.route("/")
@security.admin_required
def dashboard():
    db, f = get_db(), _filters()
    where, params = _where(f)
    per_page = current_app.config["PER_PAGE"]
    total = db.execute("SELECT COUNT(*) FROM service_requests r JOIN users u ON u.id = r.user_id" + where,
                       params).fetchone()[0]
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(max(request.args.get("page", 1, type=int), 1), pages)
    rows = db.execute(
        "SELECT r.*, u.full_name FROM service_requests r JOIN users u ON u.id = r.user_id" + where +
        " ORDER BY CASE r.priority WHEN 'Urgent' THEN 0 WHEN 'High' THEN 1 WHEN 'Normal' THEN 2 ELSE 3 END, r.id DESC"
        " LIMIT ? OFFSET ?", params + [per_page, (page - 1) * per_page]).fetchall()
    qs = {k: v for k, v in f.items() if v}   # only the filters that are actually set
    return render_template("admin/dashboard.html", requests=rows, f=f, qs=qs, page=page, pages=pages, total=total,
                           stats=services.overall_stats(db), overdue=services.overdue_ids(db))


@bp.route("/analytics")
@security.admin_required
def analytics():
    db = get_db()
    return render_template(
        "admin/analytics.html",
        stats=services.overall_stats(db),
        avg_days=services.average_resolution_days(db),
        by_category=services.breakdown(db, "category", list(CATEGORIES)),
        by_county=services.breakdown(db, "sub_county", SUB_COUNTIES),
        by_priority=services.breakdown(db, "priority", PRIORITIES),
        trend=services.daily_trend(db),
        satisfaction=services.satisfaction(db),
        overdue=len(services.overdue_ids(db)))


@bp.route("/requests/<int:request_id>/update", methods=["POST"])
@security.admin_required
def update(request_id):
    db = get_db()
    row = db.execute("SELECT * FROM service_requests WHERE id = ?", (request_id,)).fetchone()
    if not row:
        abort(404)
    status = request.form.get("status", row["status"])
    priority = request.form.get("priority", row["priority"])
    if status not in STATUSES or priority not in PRIORITIES:
        abort(400)
    error = services.apply_admin_update(
        db, row, session["name"], status, priority,
        request.form.get("department", row["department"]).strip()[:80],
        request.form.get("public_note", "").strip()[:500],
        request.form.get("internal_note", "").strip()[:500])
    if error:
        flash(error, "error")
    else:
        db.commit()
        flash("Request updated." + (" The citizen has been notified." if status != row["status"] else ""), "success")
    return redirect(url_for("citizen.detail", request_id=request_id))


@bp.route("/export.csv")
@security.admin_required
def export_csv():
    """Download the (filtered) queue as a spreadsheet-friendly CSV file."""
    f = _filters()
    where, params = _where(f)
    rows = get_db().execute(
        "SELECT r.reference, r.category, r.subject, r.location, r.sub_county, r.priority, r.status, "
        "r.department, u.full_name, u.email, r.created_at, r.resolved_at "
        "FROM service_requests r JOIN users u ON u.id = r.user_id" + where + " ORDER BY r.id DESC", params).fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Reference", "Category", "Subject", "Location", "Sub-county", "Priority", "Status",
                     "Department", "Citizen", "Email", "Created (UTC)", "Resolved (UTC)"])
    for r in rows:
        # Prefix cells starting with = + - @ so Excel never runs them as formulas.
        writer.writerow([("'" + str(v)) if isinstance(v, str) and v[:1] in "=+-@" else v for v in tuple(r)])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=hudumalink-requests.csv"})
