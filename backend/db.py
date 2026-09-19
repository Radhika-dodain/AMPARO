"""
The reports database — one SQLite file, no server, no migrations.

Deliberately tiny. The street map lives in memory; the only thing that needs
to survive a restart is what users have reported.
"""

# WHAT GOES IN HERE:
# - create the reports table on first run if it isn't there:
#   id, latitude, longitude, category, description, session_id, created_at
# - session_id matters: without it the "your history" list has no way to show
#   a user only their own reports
# - store timestamps in a way that doesn't come out 5.5 hours off — SQLite's
#   built-in default is UTC and will confuse everyone reading Indian times
# - small helpers: insert a report, fetch all reports, fetch reports for one
#   session
# - open and CLOSE connections properly; leaving them open leaks handles until
#   the server falls over

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    category    TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    session_id  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_session ON reports(session_id);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at);
"""


@contextmanager
def connect(path: Path | None = None):
    """
    Open a connection, and always close it again.

    The `with` block is the point. Connections left open leak file handles until
    the process runs out of them, which shows up as a server that worked fine
    all afternoon and then stopped.
    """
    path = Path(path or settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: Path | None = None) -> None:
    """Create the table on first run. Safe to call every startup."""
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def _now_utc_iso() -> str:
    """
    Timestamps are stored as UTC, with the timezone written into the text.

    SQLite's own CURRENT_TIMESTAMP is UTC but says nothing about it, so every
    time displays 5.5 hours out in India and nobody can tell whether it is a
    display bug or a real one. Storing the offset removes the guesswork.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_local(created_at: str) -> str:
    """Same moment, shifted for display. Stored UTC, shown local."""
    try:
        when = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return created_at
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    shifted = when + timedelta(hours=settings.display_utc_offset_hours)
    return shifted.strftime("%Y-%m-%d %H:%M")


def insert_report(
    lat: float,
    lon: float,
    category: str,
    description: str = "",
    session_id: str = "",
    path: Path | None = None,
) -> dict:
    """Save one report and hand back the stored row."""
    created_at = _now_utc_iso()
    with connect(path) as conn:
        cursor = conn.execute(
            "INSERT INTO reports (lat, lon, category, description, session_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (lat, lon, category, description, session_id, created_at),
        )
        report_id = cursor.lastrowid
    return {
        "id": report_id,
        "lat": lat,
        "lon": lon,
        "category": category,
        "description": description,
        "session_id": session_id,
        "created_at": created_at,
        "created_at_local": to_local(created_at),
    }


def list_reports(
    session_id: str | None = None,
    limit: int = 200,
    path: Path | None = None,
) -> list[dict]:
    """
    Reports, newest first.

    Both filters matter: without session_id there is no way to show someone only
    their own reports, and without a limit this happily dumps thousands of rows
    at a phone.
    """
    query = "SELECT * FROM reports"
    params: list = []
    if session_id:
        query += " WHERE session_id = ?"
        params.append(session_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))

    with connect(path) as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {**dict(row), "created_at_local": to_local(row["created_at"])} for row in rows
    ]


def all_reports_for_scoring(path: Path | None = None) -> list[dict]:
    """
    Every report, stripped to just what the risk layer needs.

    No limit here on purpose - this one feeds the map, and silently ignoring the
    oldest reports would silently change where people get routed.
    """
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT lat, lon, category, created_at FROM reports"
        ).fetchall()
    return [dict(row) for row in rows]


def count_reports(path: Path | None = None) -> int:
    with connect(path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0])
