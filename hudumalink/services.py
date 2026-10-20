"""
Business logic and analytics queries.

Routes stay thin ("receive input, call a service, render a template") and the
SQL that answers questions like "how many cases are overdue?" lives here.
"""
import secrets
from datetime import datetime, timezone

from .constants import ALLOWED_TRANSITIONS, CATEGORIES, OPEN_STATUSES, STATUSES, SUB_COUNTIES
from .db import utcnow


def make_reference() -> str:
    """Human-friendly, hard-to-guess tracking ID, e.g. ``HL-261020-9F3A1C``."""
    return "HL-" + datetime.now(timezone.utc).strftime("%y%m%d") + "-" + secrets.token_hex(3).upper()


def parse_ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


# --- Request lifecycle ------------------------------------------------------
def create_request(db, user, form, image_filename: str) -> str:
    """Insert a new request and its first history entry; return the reference."""
    reference, now = make_reference(), utcnow()
    category = form["category"]
    cur = db.execute(
        "INSERT INTO service_requests (reference, user_id, category, subject, description, location, "
        "sub_county, priority, image_filename, status, department, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?, ?)",
        (reference, user["id"], category, form["subject"], form["description"], form["location"],
         form["sub_county"], form["priority"], image_filename,
         CATEGORIES[category]["department"], now, now),
    )
    add_history(db, cur.lastrowid, "", "Pending", "Request submitted by citizen.", user["full_name"])
    return reference


def add_history(db, request_id, old, new, note, who) -> None:
    db.execute(
        "INSERT INTO status_history (request_id, old_status, new_status, note, changed_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)", (request_id, old, new, note, who, utcnow()))


def apply_admin_update(db, row, admin_name, status, priority, department, public_note, internal_note):
    """
    Apply a staff update. Returns an error string, or None on success.
    Status changes are validated against ALLOWED_TRANSITIONS, recorded in the
    timeline, and trigger an in-app notification to the citizen.
    """
    now = utcnow()
    changed = status != row["status"]
    if changed and status not in ALLOWED_TRANSITIONS[row["status"]]:
        return f"A request cannot move from {row['status']} to {status}."
    resolved_at = now if (changed and status == "Resolved") else (None if changed else row["resolved_at"])

    db.execute(
        "UPDATE service_requests SET status=?, priority=?, department=?, public_note=?, internal_note=?, "
        "updated_at=?, resolved_at=? WHERE id=?",
        (status, priority, department, public_note, internal_note, now, resolved_at, row["id"]))

    if changed:
        add_history(db, row["id"], row["status"], status, public_note, admin_name)
        db.execute(
            "INSERT INTO notifications (user_id, request_id, message, created_at) VALUES (?, ?, ?, ?)",
            (row["user_id"], row["id"],
             f"Your request {row['reference']} is now “{status}”.", now))
    return None


# --- Analytics --------------------------------------------------------------
def overall_stats(db, user_id: int | None = None) -> dict:
    """Headline counters. Pass ``user_id`` to scope them to one citizen."""
    where, args = ("WHERE user_id = ?", (user_id,)) if user_id else ("", ())
    counts = {s: 0 for s in STATUSES}
    for row in db.execute(f"SELECT status, COUNT(*) n FROM service_requests {where} GROUP BY status", args):
        counts[row["status"]] = row["n"]
    total = sum(counts.values())
    closed = counts["Resolved"] + counts["Rejected"]
    return {
        "total": total,
        "pending": counts["Pending"],
        "progress": counts["In Progress"],
        "resolved": counts["Resolved"],
        "rejected": counts["Rejected"],
        "open": counts["Pending"] + counts["In Progress"],
        "closed": closed,
        "resolution_rate": round(100 * counts["Resolved"] / total) if total else 0,
        "by_status": counts,
    }


def public_stats(db) -> dict:
    """Anonymous numbers shown on the public home page."""
    s = overall_stats(db)
    avg = average_resolution_days(db)
    s["avg_days"] = avg
    return s


def average_resolution_days(db) -> float | None:
    rows = db.execute("SELECT created_at, resolved_at FROM service_requests WHERE resolved_at IS NOT NULL").fetchall()
    if not rows:
        return None
    days = [(parse_ts(r["resolved_at"]) - parse_ts(r["created_at"])).total_seconds() / 86400 for r in rows]
    return round(sum(days) / len(days), 1)


def breakdown(db, column: str, labels: list[str]) -> list[dict]:
    """Count requests per value of ``column`` (whitelisted, never user input)."""
    assert column in {"category", "sub_county", "priority"}
    found = {r[0]: r[1] for r in db.execute(f"SELECT {column}, COUNT(*) FROM service_requests GROUP BY {column}")}
    top = max(found.values(), default=0) or 1
    return [{"label": l, "count": found.get(l, 0), "pct": round(100 * found.get(l, 0) / top)} for l in labels]


def overdue_ids(db) -> set[int]:
    """IDs of open requests older than their category's service-level target."""
    now = datetime.now(timezone.utc)
    late = set()
    for r in db.execute("SELECT id, category, created_at FROM service_requests WHERE status IN (?, ?)", OPEN_STATUSES):
        sla = CATEGORIES.get(r["category"], {}).get("sla_days", 7)
        if (now - parse_ts(r["created_at"])).days >= sla:
            late.add(r["id"])
    return late


def daily_trend(db, days: int = 14) -> dict:
    """Submitted vs resolved per day for the last ``days`` days, as SVG points."""
    from datetime import timedelta
    today = datetime.now(timezone.utc).date()
    labels = [(today - timedelta(days=i)) for i in range(days - 1, -1, -1)]
    submitted = {d: 0 for d in labels}
    resolved = {d: 0 for d in labels}
    for r in db.execute("SELECT created_at, resolved_at FROM service_requests"):
        c = parse_ts(r["created_at"]).date()
        if c in submitted:
            submitted[c] += 1
        if r["resolved_at"]:
            s = parse_ts(r["resolved_at"]).date()
            if s in resolved:
                resolved[s] += 1
    peak = max([*submitted.values(), *resolved.values(), 1])
    w, h, pad = 560, 180, 16

    def points(series):
        step = (w - 2 * pad) / (days - 1)
        return " ".join(f"{pad + i * step:.1f},{h - pad - (series[d] / peak) * (h - 2 * pad):.1f}"
                        for i, d in enumerate(labels))

    return {"w": w, "h": h, "submitted": points(submitted), "resolved": points(resolved),
            "start": labels[0].strftime("%d %b"), "end": labels[-1].strftime("%d %b"), "peak": peak}


def satisfaction(db) -> dict:
    row = db.execute("SELECT AVG(rating) a, COUNT(rating) n FROM service_requests WHERE rating IS NOT NULL").fetchone()
    return {"average": round(row["a"], 1) if row["a"] else None, "count": row["n"]}
