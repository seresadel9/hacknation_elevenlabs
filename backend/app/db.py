"""SQLite persistence. The knowledge graph is modelled explicitly as typed nodes + typed edges."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    workflow_name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('lockin', 'live')),
    status TEXT NOT NULL,
    script TEXT,                      -- name of the seeded demo script, or NULL for a custom workflow
    speed REAL NOT NULL DEFAULT 1,    -- work-clock compression for seeded playback
    screen_share INTEGER NOT NULL DEFAULT 0,
    started_at REAL,
    paused_at REAL,
    paused_total REAL NOT NULL DEFAULT 0,
    offset_s REAL NOT NULL DEFAULT 0,
    ended_work_s REAL,
    script_cursor INTEGER NOT NULL DEFAULT 0,
    off_record INTEGER NOT NULL DEFAULT 0,
    off_record_since REAL,
    last_live_question_s REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    t_s REAL NOT NULL,
    kind TEXT NOT NULL,               -- action | decision | note | transcript | screen_change | marker | pause
    source TEXT NOT NULL,             -- observed | expert | simulated | vision | system
    activity TEXT,                    -- navigating | reading | typing | speaking | idle
    text TEXT NOT NULL,
    data TEXT NOT NULL DEFAULT '{}',
    off_record INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    gap_types TEXT NOT NULL,          -- JSON list
    text TEXT NOT NULL,
    trigger_event_id TEXT,
    case_ref TEXT,
    priority REAL NOT NULL,
    status TEXT NOT NULL,             -- queued | asked_live | answered | deferred | skipped | covered
    phase TEXT,                       -- live | debrief (when it was asked)
    answer TEXT,
    answered_at TEXT,
    covered_reason TEXT,
    targets TEXT NOT NULL DEFAULT '{}',
    sample_answer TEXT,
    created_t_s REAL NOT NULL,
    UNIQUE(session_id, key)
);

CREATE TABLE IF NOT EXISTS pacing_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    t_s REAL NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teachback_items (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    node_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    original_text TEXT NOT NULL,
    provenance TEXT NOT NULL,         -- ai_inference | expert_statement | observed
    generator TEXT NOT NULL,          -- deterministic | llm
    sources TEXT NOT NULL DEFAULT '[]',
    parts TEXT NOT NULL DEFAULT '[]',
    confidence TEXT NOT NULL,         -- high | medium | low
    unresolved TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pending'  -- pending | confirmed | edited | rejected
);

CREATE TABLE IF NOT EXISTS nodes (
    key TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('skill', 'decision', 'guardrail', 'step', 'case', 'evidence')),
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('draft', 'needs_confirmation', 'confirmed')),
    card TEXT NOT NULL DEFAULT '{}',
    session_id TEXT,
    seeded INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src TEXT NOT NULL REFERENCES nodes(key) ON DELETE CASCADE,
    dst TEXT NOT NULL REFERENCES nodes(key) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('prerequisite_for', 'depends_on', 'demonstrated_by',
                                       'constrained_by', 'exception_to', 'supported_by_evidence')),
    provenance TEXT NOT NULL DEFAULT 'ai_inference',
    UNIQUE(src, dst, type)
);

CREATE TABLE IF NOT EXISTS attempts (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    level_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('learn', 'practice')),
    path TEXT NOT NULL DEFAULT '[]',
    interventions TEXT NOT NULL DEFAULT '[]',
    action_id TEXT NOT NULL,
    reason_id TEXT,
    action_correct INTEGER NOT NULL,
    reason_correct INTEGER NOT NULL,
    guardrails_missed TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mastery (
    learner_id TEXT NOT NULL,
    skill_key TEXT NOT NULL,
    status TEXT NOT NULL,             -- practiced | mastered
    evidence TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (learner_id, skill_key)
);

CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    alias TEXT NOT NULL,
    consent_at TEXT NOT NULL,
    status TEXT NOT NULL,             -- in_progress | submitted
    started_at TEXT NOT NULL,
    submitted_at TEXT,
    retain_until TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trial_responses (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    gl_code TEXT,
    rationale TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT '[]',
    time_spent_s REAL,
    created_at TEXT NOT NULL,
    UNIQUE(candidate_id, task_id)
);
"""

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _connect() -> sqlite3.Connection:
    path = get_settings().database_path
    conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL" if path != ":memory:" else "PRAGMA journal_mode = MEMORY")
    conn.executescript(SCHEMA)
    return conn


def init_db(reset: bool = False) -> None:
    global _conn
    with _lock:
        if _conn is not None and reset:
            _conn.close()
            _conn = None
        if _conn is None:
            _conn = _connect()


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    """Serialised transaction. SQLite + one process is plenty for the MVP."""
    init_db()
    assert _conn is not None
    with _lock:
        _conn.execute("BEGIN")
        try:
            yield _conn
        except BaseException:
            _conn.execute("ROLLBACK")
            raise
        else:
            _conn.execute("COMMIT")


def wipe_all() -> None:
    with tx() as c:
        for table in (
            "trial_responses",
            "candidates",
            "mastery",
            "attempts",
            "edges",
            "nodes",
            "teachback_items",
            "pacing_log",
            "questions",
            "events",
            "sessions",
        ):
            c.execute(f"DELETE FROM {table}")


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    return json.loads(value)


def row_dict(row: sqlite3.Row | None, json_fields: tuple[str, ...] = ()) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for f in json_fields:
        if f in d:
            d[f] = loads(d[f], None)
    return d
