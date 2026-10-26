"""
Database layer: connection handling, schema, and demo seed data.

We use Python's built-in ``sqlite3`` (no ORM) so every query is visible,
parameterised, and easy to explain in a code review.
"""
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import current_app, g
from werkzeug.security import generate_password_hash

from .constants import CATEGORIES, SUB_COUNTIES

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT NOT NULL DEFAULT '',
    sub_county    TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'citizen' CHECK (role IN ('citizen', 'admin')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_requests (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    reference      TEXT NOT NULL UNIQUE,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    category       TEXT NOT NULL,
    subject        TEXT NOT NULL,
    description    TEXT NOT NULL,
    location       TEXT NOT NULL,
    sub_county     TEXT NOT NULL DEFAULT '',
    priority       TEXT NOT NULL DEFAULT 'Normal',
    image_filename TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'Pending',
    department     TEXT NOT NULL DEFAULT '',
    public_note    TEXT NOT NULL DEFAULT '',   -- visible to the citizen
    internal_note  TEXT NOT NULL DEFAULT '',   -- staff only
    rating         INTEGER,                    -- citizen feedback, 1-5
    feedback       TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    resolved_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_requests_user   ON service_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_status ON service_requests(status);

CREATE TABLE IF NOT EXISTS status_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  INTEGER NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    old_status  TEXT NOT NULL DEFAULT '',
    new_status  TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    changed_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    request_id  INTEGER NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    message     TEXT NOT NULL,
    is_read     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);
"""


def utcnow() -> str:
    """Current UTC time as an ISO-8601 string (what we store in the DB)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    """Return the per-request connection, creating it on first use."""
    if "db" not in g:
        os.makedirs(os.path.dirname(current_app.config["DATABASE_PATH"]), exist_ok=True)
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app) -> None:
    """Register database cleanup with the Flask application."""
    app.teardown_appcontext(close_db)


def init_db() -> None:
    """Create tables, then make sure there is at least one administrator."""
    db = get_db()
    db.executescript(SCHEMA)
    _ensure_admin(db)
    if current_app.config["DEMO_MODE"]:
        _seed_demo_data(db)
    db.commit()


def _ensure_admin(db: sqlite3.Connection) -> None:
    """Create the administrator named in ADMIN_EMAIL / ADMIN_PASSWORD."""
    email = current_app.config["ADMIN_EMAIL"]
    password = current_app.config["ADMIN_PASSWORD"]
    if not (email and password):
        return
    if not db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        db.execute(
            "INSERT INTO users (full_name, email, password_hash, role, created_at) "
            "VALUES (?, ?, ?, 'admin', ?)",
            ("County Administrator", email, generate_password_hash(password), utcnow()),
        )


def _seed_demo_data(db: sqlite3.Connection) -> None:
    """
    Populate a believable demo so markers can explore every screen at once.
    Runs only when the database has no users yet, so it never overwrites data.
    """
    # Gunicorn can boot more than one worker at the same time. Serialize the
    # empty-database check and first insert so both workers cannot seed twice.
    db.execute("BEGIN IMMEDIATE")
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return

    now = datetime.now(timezone.utc)
    stamp = lambda days_ago: (now - timedelta(days=days_ago)).isoformat(timespec="seconds")

    db.execute(
        "INSERT INTO users (full_name, email, phone, sub_county, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'admin', ?)",
        ("Demo Administrator", "admin@hudumalink.demo", "0700000001", "Kiharu",
         generate_password_hash("Admin@2026"), stamp(30)),
    )
    db.execute(
        "INSERT INTO users (full_name, email, phone, sub_county, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'citizen', ?)",
        ("Wanjiru Njeri", "citizen@hudumalink.demo", "0700000002", "Kigumo",
         generate_password_hash("Citizen@2026"), stamp(28)),
    )

    # (category, subject, location, sub-county, priority, status, days_ago)
    samples = [
        ("Streetlight Fault", "Streetlight out near Kenol stage", "Kenol Market, Mombasa Rd", "Kigumo", "High", "Resolved", 12),
        ("Water Supply Problem", "No water for three days", "Kiriaini Estate, Block C", "Mathioya", "Urgent", "In Progress", 4),
        ("Garbage Collection", "Uncollected garbage at the market", "Murang'a Town Market", "Kiharu", "Normal", "Pending", 2),
        ("Roads & Drainage", "Pothole damaging vehicles", "Kangari–Kandara Road", "Kandara", "High", "In Progress", 9),
        ("Public Health & Sanitation", "Blocked public toilet", "Maragua Bus Park", "Maragwa", "Normal", "Resolved", 15),
        ("Streetlight Fault", "Three lamps flickering", "Kangema Town Centre", "Kangema", "Low", "Pending", 1),
        ("Roads & Drainage", "Drainage overflowing onto road", "Gatanga Junction", "Gatanga", "Urgent", "Pending", 6),
        ("Garbage Collection", "Illegal dumping beside river", "Sagana Bridge", "Kigumo", "Normal", "Resolved", 20),
        ("Water Supply Problem", "Burst pipe wasting water", "Kenol–Sagana Road", "Kigumo", "Urgent", "Resolved", 8),
        ("Other Public Service", "Request for a new notice board", "Kiharu Ward Office", "Kiharu", "Low", "Rejected", 11),
    ]
    random.seed(7)  # deterministic references keep tests and screenshots stable
    for i, (cat, subject, loc, sub, prio, status, ago) in enumerate(samples, start=1):
        created = stamp(ago)
        resolved = stamp(max(ago - 3, 0)) if status == "Resolved" else None
        ref = f"HL-{(now - timedelta(days=ago)).strftime('%y%m%d')}-{random.randrange(16**4):04X}"
        cur = db.execute(
            "INSERT INTO service_requests (reference, user_id, category, subject, description, location, "
            "sub_county, priority, status, department, public_note, rating, created_at, updated_at, resolved_at) "
            "VALUES (?, 2, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ref, cat, subject,
             f"Reported by a resident: {subject.lower()}. Please attend as soon as possible.",
             loc, sub, prio, status, CATEGORIES[cat]["department"],
             "Crew dispatched and the issue has been fixed." if status == "Resolved" else "",
             5 if status == "Resolved" and i % 2 else None,
             created, resolved or created, resolved),
        )
        rid = cur.lastrowid
        db.execute("INSERT INTO status_history (request_id, new_status, note, changed_by, created_at) "
                   "VALUES (?, 'Pending', 'Request submitted by citizen.', 'Wanjiru Njeri', ?)", (rid, created))
        if status in ("In Progress", "Resolved"):
            db.execute("INSERT INTO status_history (request_id, old_status, new_status, note, changed_by, created_at) "
                       "VALUES (?, 'Pending', 'In Progress', 'Assigned to the field team.', 'Demo Administrator', ?)",
                       (rid, stamp(max(ago - 1, 0))))
        if status == "Resolved":
            db.execute("INSERT INTO status_history (request_id, old_status, new_status, note, changed_by, created_at) "
                       "VALUES (?, 'In Progress', 'Resolved', 'Work completed and verified.', 'Demo Administrator', ?)",
                       (rid, resolved))
        if status == "Rejected":
            db.execute("INSERT INTO status_history (request_id, old_status, new_status, note, changed_by, created_at) "
                       "VALUES (?, 'Pending', 'Rejected', 'Outside the scope of county services.', 'Demo Administrator', ?)",
                       (rid, stamp(max(ago - 1, 0))))
