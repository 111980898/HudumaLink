"""Jinja filters that turn raw database values into friendly text."""
from datetime import datetime, timezone

from markupsafe import Markup


def _dt(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def register_filters(app):
    @app.template_filter("date")
    def fmt_date(value):
        """2026-10-20T05:00:00+00:00 -> 20 Oct 2026"""
        return _dt(value).strftime("%d %b %Y") if value else "—"

    @app.template_filter("datetime")
    def fmt_datetime(value):
        """-> 20 Oct 2026, 08:00 (shown in East Africa Time, UTC+3)."""
        if not value:
            return "—"
        from datetime import timedelta
        return (_dt(value) + timedelta(hours=3)).strftime("%d %b %Y, %H:%M")

    @app.template_filter("ago")
    def time_ago(value):
        """-> '3 days ago' / 'just now'."""
        if not value:
            return "—"
        seconds = (datetime.now(timezone.utc) - _dt(value)).total_seconds()
        for span, name in ((86400, "day"), (3600, "hour"), (60, "minute")):
            if seconds >= span:
                n = int(seconds // span)
                return f"{n} {name}{'s' if n != 1 else ''} ago"
        return "just now"

    @app.template_filter("slug")
    def slug(value):
        """'In Progress' -> 'in-progress' (used for CSS class names)."""
        return str(value).lower().replace(" ", "-")

    @app.template_filter("stars")
    def stars(value):
        return Markup("★" * int(value) + "☆" * (5 - int(value))) if value else ""
