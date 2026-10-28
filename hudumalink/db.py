"""
Database layer for Huduma Link.

SQLite remains the lightweight local/test backend. When DATABASE_URL is present,
the same parameterised queries run against Neon PostgreSQL so registrations,
requests, tracking history, notifications, and admin updates persist across
Vercel serverless instances.
"""
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import current_app, g
from werkzeug.security import generate_password_hash

from .constants import CATEGORIES

try:  # Optional locally; production installs psycopg from requirements.txt.
    import psycopg
    from psycopg import IntegrityError as PostgresIntegrityError
except ImportError:  # pragma: no cover - exercised only in SQLite-only installs.
    class PostgresIntegrityError(Exception):
        pass

    psycopg = None


class HybridRow(dict):
    """A PostgreSQL row that supports both row['column'] and row[0]."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def hybrid_row(cursor):
    if cursor.description is None:
        return lambda values: values
    columns = [column.name for column in cursor.description]

    def make_row(values):
        return HybridRow(zip(columns, values))

    return make_row


DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError, PostgresIntegrityError)

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
    public_note    TEXT NOT NULL DEFAULT '',
    internal_note  TEXT NOT NULL DEFAULT '',
    rating         INTEGER,
    feedback       TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    resolved_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_requests_user ON service_requests(user_id);
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
POSTGRES_SCHEMA = SCHEMA.replace(
    "INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY"
)


class DatabaseConnection:
    """Small compatibility wrapper around sqlite3 or psycopg."""
    def __init__(self, connection, postgres=False):
        self.connection = connection
        self.is_postgres = postgres

    def execute(self, sql, params=()):
        if self.is_postgres:
            sql = sql.replace("?", "%s")
        return self.connection.execute(sql, params)

    def executescript(self, script):
        if not self.is_postgres:
            return self.connection.executescript(script)
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                self.connection.execute(statement)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def insert_id(cursor):
    """Read an inserted primary key from either SQLite or PostgreSQL."""
    lastrowid = getattr(cursor, "lastrowid", None)
    if lastrowid is not None:
        return lastrowid
    row = cursor.fetchone()
    return row[0] if row else None


def is_postgres(db) -> bool:
    return bool(getattr(db, "is_postgres", False))


def get_db() -> DatabaseConnection:
    """Return the per-request database connection."""
    if "db" not in g:
        dsn = current_app.config.get("DATABASE_URL", "").strip()
        if dsn:
            if psycopg is None:
                raise RuntimeError("psycopg is required when DATABASE_URL is configured")
            connection = psycopg.connect(dsn, row_factory=hybrid_row, connect_timeout=10)
            g.db = DatabaseConnection(connection, postgres=True)
        else:
            path = current_app.config["DATABASE_PATH"]
            os.makedirs(os.path.dirname(path), exist_ok=True)
            connection = sqlite3.connect(path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            g.db = DatabaseConnection(connection)
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)


def init_db() -> None:
    db = get_db()
    db.executescript(POSTGRES_SCHEMA if is_postgres(db) else SCHEMA)
    _ensure_admin(db)
    if current_app.config["DEMO_MODE"]:
        _seed_demo_data(db)
    db.commit()


def _ensure_admin(db) -> None:
    email = current_app.config["ADMIN_EMAIL"]
    password = current_app.config["ADMIN_PASSWORD"]
    if not (email and password):
        return
    db.execute(
        "INSERT INTO users (full_name, email, password_hash, role, created_at) "
        "VALUES (?, ?, ?, 'admin', ?) ON CONFLICT (email) DO NOTHING",
        ("County Administrator", email, generate_password_hash(password), utcnow()),
    )


def _seed_demo_data(db) -> None:
    """Populate the first empty database once for assessment/demo use."""
    if is_postgres(db):
        db.execute("SELECT pg_advisory_xact_lock(458721)")
    else:
        db.execute("BEGIN IMMEDIATE")
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return

    now = datetime.now(timezone.utc)
    stamp = lambda days_ago: (now - timedelta(days=days_ago)).isoformat(timespec="seconds")
    db.execute(
        "INSERT INTO users (full_name, email, phone, sub_county, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'admin', ?) ON CONFLICT (email) DO NOTHING",
        ("Demo Administrator", "admin@hudumalink.demo", "0700000001", "Kiharu",
         generate_password_hash("Admin@2026"), stamp(30)),
    )
    db.execute(
        "INSERT INTO users (full_name, email, phone, sub_county, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'citizen', ?) ON CONFLICT (email) DO NOTHING",
        ("Wanjiru Njeri", "citizen@hudumalink.demo", "0700000002", "Kigumo",
         generate_password_hash("Citizen@2026"), stamp(28)),
    )

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
    random.seed(7)
    for i, (cat, subject, loc, sub, prio, status, ago) in enumerate(samples, start=1):
        created = stamp(ago)
        resolved = stamp(max(ago - 3, 0)) if status == "Resolved" else None
        ref = f"HL-{(now - timedelta(days=ago)).strftime('%y%m%d')}-{random.randrange(16**4):04X}"
        cur = db.execute(
            "INSERT INTO service_requests (reference, user_id, category, subject, description, location, "
            "sub_county, priority, status, department, public_note, rating, created_at, updated_at, resolved_at) "
            "VALUES (?, 2, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
            (ref, cat, subject,
             f"Reported by a resident: {subject.lower()}. Please attend as soon as possible.",
             loc, sub, prio, status, CATEGORIES[cat]["department"],
             "Crew dispatched and the issue has been fixed." if status == "Resolved" else "",
             5 if status == "Resolved" and i % 2 else None,
             created, resolved or created, resolved),
        )
        rid = insert_id(cur)
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
