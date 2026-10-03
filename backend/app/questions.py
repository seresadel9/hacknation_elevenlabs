"""Evidence-based gap questions: generation, coverage detection, prioritisation and rendering.

Questions are anchored to observed moments. Before any question is revealed we re-check whether the expert has
already answered it in their own words during the session — if so it is marked "covered" and never asked.
"""

from __future__ import annotations

import math
import re
import sqlite3
from typing import Any

from . import demo_script as demo
from .db import dumps, loads, new_id
from .language import detect_gap_types, fmt_clock

GENERIC_PENALTY = 2.0

CUSTOM_TEMPLATES: dict[str, tuple[str, str]] = {
    # gap_type: (debrief text, short live text)
    "why": ('At {t} you noted "{quote}". Why did you decide it that way?', "Why that call at {t}?"),
    "change_condition": (
        'Looking at {t} ("{quote}") — what would have to be different for you to decide otherwise?',
        "What would change your decision here?",
    ),
    "threshold": (
        'At {t} you mentioned "{number}". Is that a hard limit — and exactly how is it measured?',
        "Is {number} a hard limit?",
    ),
    "escalation": (
        "In the situation at {t}, when would you stop and ask someone instead of deciding yourself?",
        "When would you escalate this instead?",
    ),
    "never": (
        'Is there anything someone must never do in the situation at {t} ("{quote}")?',
        "Anything that must never be done here?",
    ),
}


def priority_for(gap_types: list[str], amount: float | None, hesitation: bool, generic: bool) -> float:
    weights = sorted((demo.GAP_WEIGHTS.get(g, 2.0) for g in gap_types), reverse=True)
    p = weights[0] + 0.3 * (len(weights) - 1)
    if amount:
        p += 0.5 * math.log10(amount + 1)
    if hesitation:
        p += 0.8
    if generic:
        p -= GENERIC_PENALTY
    return round(p, 3)


def _case_hesitated(conn: sqlite3.Connection, session_id: str, case_ref: str | None) -> bool:
    if not case_ref:
        return False
    for r in conn.execute("SELECT data FROM events WHERE session_id=? AND off_record=0", (session_id,)).fetchall():
        d = loads(r["data"], {})
        if d.get("case") == case_ref and d.get("hesitation"):
            return True
    return False


def queue_script_gaps(conn: sqlite3.Connection, session_id: str, event_id: str, ev: dict[str, Any]) -> None:
    """Called as a seeded/observed decision moment is captured. Queues silently — never shown live in Lock-In."""
    for key in ev.get("gaps", []):
        spec = demo.GAPS[key]
        amount = (ev.get("data") or {}).get("amount")
        prio = priority_for(
            spec["gap_types"],
            amount,
            _case_hesitated(conn, session_id, ev.get("case")),
            generic=key == "q-approval-limit",
        )
        conn.execute(
            """INSERT OR IGNORE INTO questions
               (id, session_id, key, gap_types, text, trigger_event_id, case_ref, priority, status, targets,
                sample_answer, created_t_s)
               VALUES (?,?,?,?,?,?,?,?, 'queued', ?, ?, ?)""",
            (
                new_id("q"),
                session_id,
                key,
                dumps(spec["gap_types"]),
                spec["text"],
                event_id,
                ev.get("case"),
                prio,
                dumps(spec["targets"]),
                spec["sample_answer"],
                ev["t"],
            ),
        )


def queue_custom_gaps(conn: sqlite3.Connection, session_id: str, event: dict[str, Any], workflow_skill: str) -> None:
    """Custom workflows: every expert note opens the gaps it does not already answer itself."""
    covered = detect_gap_types(event["text"])
    numbers = re.findall(r"[€$£]?\s?\d[\d.,]*\s?(?:%|€|eur|k)?", event["text"], flags=re.I)
    candidates: list[tuple[str, list[str], bool]] = [
        (f"c-why-{event['id']}", ["why"], False),
        (f"c-change-{event['id']}", ["change_condition"], False),
    ]
    if numbers:
        candidates.append((f"c-threshold-{event['id']}", ["threshold"], False))
    # Session-wide guardrail questions are asked once, anchored to the first note that raises them.
    candidates += [("c-escalation", ["escalation"], True), ("c-never", ["never"], True)]
    for key, gaps, generic in candidates:
        if all(g in covered for g in gaps):
            continue
        conn.execute(
            """INSERT OR IGNORE INTO questions
               (id, session_id, key, gap_types, text, trigger_event_id, case_ref, priority, status, targets,
                created_t_s)
               VALUES (?,?,?,?,?,?,?,?, 'queued', ?, ?)""",
            (
                new_id("q"),
                session_id,
                key,
                dumps(gaps),
                CUSTOM_TEMPLATES[gaps[0]][0],
                event["id"],
                None,
                priority_for(gaps, None, False, generic),
                dumps({"skill": workflow_skill, "node": workflow_skill}),
                event["t_s"],
            ),
        )


def _event(conn: sqlite3.Connection, event_id: str | None) -> sqlite3.Row | None:
    if not event_id:
        return None
    return conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()


def _case_notes(conn: sqlite3.Connection, session_id: str, case_ref: str | None) -> list[sqlite3.Row]:
    rows = conn.execute(
        "SELECT * FROM events WHERE session_id=? AND kind IN ('note','transcript') AND off_record=0 ORDER BY seq",
        (session_id,),
    ).fetchall()
    if case_ref is None:
        return list(rows)
    return [r for r in rows if loads(r["data"], {}).get("case") == case_ref]


def render(conn: sqlite3.Connection, q: sqlite3.Row, live: bool = False) -> str:
    """Fill a question template with the actual evidence (timestamps, the expert's own words)."""
    trig = _event(conn, q["trigger_event_id"])
    t = fmt_clock(trig["t_s"]) if trig else "the start"
    notes = _case_notes(conn, q["session_id"], q["case_ref"]) if q["case_ref"] else []
    note = notes[-1]["text"].rstrip(".!") if notes else ""
    fields: dict[str, str] = {"t": t, "note": note, "quote": trig["text"] if trig else "", "t_other": "earlier"}
    if q["key"] in demo.GAPS:
        spec = demo.GAPS[q["key"]]
        if live and spec.get("live_text"):
            return spec["live_text"]
        other = spec.get("other_event")
        if other:
            row = conn.execute(
                "SELECT t_s FROM events WHERE session_id=? AND json_extract(data,'$.script_key')=? AND off_record=0",
                (q["session_id"], other),
            ).fetchone()
            fields["t_other"] = fmt_clock(row["t_s"]) if row else "earlier"
        text = spec["text"]
        if not note:
            text = re.sub(r" and said \"\{note\}\"", "", text)
        return text.format(**fields)
    gaps = loads(q["gap_types"], [])
    nums = re.findall(r"[€$£]?\s?\d[\d.,]*\s?(?:%|€|eur|k)?", fields["quote"], flags=re.I)
    fields["number"] = nums[0].strip() if nums else "that number"
    tmpl = CUSTOM_TEMPLATES[gaps[0]][1 if live else 0]
    return tmpl.format(**fields)


def apply_coverage(conn: sqlite3.Connection, session_id: str) -> list[dict[str, Any]]:
    """Mark queued questions the expert already answered in their own words. Returns what was skipped and why."""
    covered: list[dict[str, Any]] = []
    for q in conn.execute(
        "SELECT * FROM questions WHERE session_id=? AND status IN ('queued','deferred')", (session_id,)
    ).fetchall():
        trig = _event(conn, q["trigger_event_id"])
        if trig is None:
            continue
        gaps = set(loads(q["gap_types"], []))
        for note in _case_notes(conn, session_id, q["case_ref"]):
            if note["seq"] < trig["seq"] or note["id"] == trig["id"]:
                continue
            if gaps <= detect_gap_types(note["text"]):
                reason = f"You already said at {fmt_clock(note['t_s'])}: “{note['text']}”"
                conn.execute("UPDATE questions SET status='covered', covered_reason=? WHERE id=?", (reason, q["id"]))
                covered.append({"key": q["key"], "reason": reason})
                break
    return covered
