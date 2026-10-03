"""Expert capture sessions: Lock-In Mode and Live Coaching.

Lock-In invariant (enforced here, on the server): while a Lock-In session is not finished, no question text ever
leaves this module — callers only get a count. Live Coaching may surface one question at a time, and only at a
natural pause, about what is on screen, with pacing of at most one question per LIVE_MIN_GAP_S of work time.
"""

from __future__ import annotations

import re
import sqlite3
import time
from typing import Any

from fastapi import HTTPException

from . import demo_script as demo
from . import integrations, mapbuilder, questions
from .db import dumps, loads, new_id, now_iso, row_dict, tx
from .language import fmt_clock

LIVE_MIN_GAP_S = 120.0  # work-clock seconds between live questions → at most 5 per 10 minutes
ACTIVE = ("active", "paused")
FINISHED = ("debrief", "review", "committed")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "workflow"


def workflow_skill_key(session: dict[str, Any] | sqlite3.Row) -> str:
    return f"s-{_slug(session['workflow_name'])}"


def get_session_row(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Session not found (it may have been discarded).")
    return row


def work_time(s: sqlite3.Row, now: float | None = None) -> float:
    if s["ended_work_s"] is not None:
        return float(s["ended_work_s"])
    if s["started_at"] is None:
        return 0.0
    ref = s["paused_at"] if s["paused_at"] is not None else (now or time.time())
    return max(0.0, (ref - s["started_at"] - s["paused_total"]) * s["speed"] + s["offset_s"])


def create_session(workflow_name: str, mode: str, use_demo_script: bool, screen_share: bool) -> dict[str, Any]:
    sid = new_id("ses")
    with tx() as c:
        c.execute(
            """INSERT INTO sessions (id, workflow_name, mode, status, script, speed, screen_share, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                sid,
                workflow_name.strip() or demo.DEMO_WORKFLOW_NAME,
                mode,
                "ready",
                demo.DEMO_SCRIPT_NAME if use_demo_script else None,
                demo.DEMO_SPEED if use_demo_script else 1.0,
                int(screen_share),
                now_iso(),
            ),
        )
    return state(sid)


def _next_seq(c: sqlite3.Connection, sid: str) -> int:
    return int(c.execute("SELECT COALESCE(MAX(seq),0)+1 FROM events WHERE session_id=?", (sid,)).fetchone()[0])


def add_event(
    c: sqlite3.Connection,
    sid: str,
    t_s: float,
    kind: str,
    source: str,
    text: str,
    activity: str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    eid = new_id("ev")
    seq = _next_seq(c, sid)
    c.execute(
        "INSERT INTO events (id, session_id, seq, t_s, kind, source, activity, text, data) VALUES (?,?,?,?,?,?,?,?,?)",
        (eid, sid, seq, t_s, kind, source, activity, text, dumps(data or {})),
    )
    return {"id": eid, "seq": seq, "t_s": t_s, "kind": kind, "source": source, "text": text, "data": data or {}}


def _log_pacing(c: sqlite3.Connection, sid: str, t: float, decision: str, reason: str) -> None:
    c.execute("INSERT INTO pacing_log (session_id, t_s, decision, reason) VALUES (?,?,?,?)", (sid, t, decision, reason))


def _maybe_ask_live(c: sqlite3.Connection, s: sqlite3.Row, t: float, case_ref: str | None) -> None:
    """Live Coaching: only at a natural pause, only about what is visible, sparse pacing."""
    if s["mode"] != "live" or s["off_record"]:
        return
    sid = s["id"]
    if c.execute("SELECT 1 FROM questions WHERE session_id=? AND status='asked_live'", (sid,)).fetchone():
        _log_pacing(c, sid, t, "held", "Previous question still open — never stack questions.")
        return
    last = s["last_live_question_s"]
    if last is not None and t - last < LIVE_MIN_GAP_S:
        _log_pacing(
            c,
            sid,
            t,
            "held",
            f"Pause detected, but the last question was {fmt_clock(t - last)} ago (min {fmt_clock(LIVE_MIN_GAP_S)}).",
        )
        return
    questions.apply_coverage(c, sid)
    rows = c.execute(
        "SELECT * FROM questions WHERE session_id=? AND status='queued' ORDER BY priority DESC", (sid,)
    ).fetchall()
    visible = [
        q
        for q in rows
        if (case_ref is None or q["case_ref"] == case_ref)
        and (q["key"] not in demo.GAPS or demo.GAPS[q["key"]].get("live_text"))
    ]
    if not visible:
        _log_pacing(c, sid, t, "silent", "Pause detected — nothing on screen needs a question.")
        return
    q = visible[0]
    c.execute("UPDATE questions SET status='asked_live', phase='live' WHERE id=?", (q["id"],))
    c.execute("UPDATE sessions SET last_live_question_s=? WHERE id=?", (t, sid))
    _log_pacing(c, sid, t, "asked", "Natural pause, about what is on screen.")


def materialize(c: sqlite3.Connection, sid: str) -> None:
    """Release seeded (simulated) observations up to the current work clock."""
    s = get_session_row(c, sid)
    if not s["script"] or s["status"] != "active":
        return
    t_now = work_time(s)
    cursor = s["script_cursor"]
    while cursor < len(demo.SCRIPT_EVENTS) and demo.SCRIPT_EVENTS[cursor]["t"] <= t_now:
        ev = demo.SCRIPT_EVENTS[cursor]
        cursor += 1
        c.execute("UPDATE sessions SET script_cursor=? WHERE id=?", (cursor, sid))
        if s["off_record"]:
            continue  # off the record: nothing is stored, no question is queued
        data = {**(ev.get("data") or {}), "case": ev.get("case"), "script_key": ev["key"], "refs": ev.get("refs", [])}
        row = add_event(
            c, sid, float(ev["t"]), ev["kind"], ev.get("source", "simulated"), ev["text"], ev.get("activity"), data
        )
        questions.queue_script_gaps(c, sid, row["id"], ev)
        if ev["kind"] == "pause":
            _maybe_ask_live(c, get_session_row(c, sid), float(ev["t"]), ev.get("case"))


def _public_event(r: sqlite3.Row) -> dict[str, Any]:
    d = loads(r["data"], {})
    return {
        "id": r["id"],
        "t_s": r["t_s"],
        "clock": fmt_clock(r["t_s"]),
        "kind": r["kind"],
        "source": r["source"],
        "activity": r["activity"],
        "text": r["text"],
        "case": d.get("case"),
        "off_record": bool(r["off_record"]),
    }


def state(sid: str) -> dict[str, Any]:
    with tx() as c:
        materialize(c, sid)
        s = get_session_row(c, sid)
        events = [
            _public_event(r)
            for r in c.execute("SELECT * FROM events WHERE session_id=? ORDER BY seq", (sid,)).fetchall()
        ]
        held = c.execute(
            "SELECT COUNT(*) FROM questions WHERE session_id=? AND status IN ('queued','deferred')", (sid,)
        ).fetchone()[0]
        asked_live = c.execute("SELECT COUNT(*) FROM questions WHERE session_id=? AND phase='live'", (sid,)).fetchone()[
            0
        ]
        live_q = None
        live_answered: list[dict[str, Any]] = []
        pacing: list[dict[str, Any]] = []
        if s["mode"] == "live":
            q = c.execute("SELECT * FROM questions WHERE session_id=? AND status='asked_live'", (sid,)).fetchone()
            if q:
                live_q = {
                    "id": q["id"],
                    "text": questions.render(c, q, live=True),
                    "gap_types": loads(q["gap_types"], []),
                    "sample_answer": q["sample_answer"],
                    "simulated": bool(s["script"]),
                }
            for q in c.execute(
                "SELECT * FROM questions WHERE session_id=? AND phase='live' AND status IN ('answered','deferred')",
                (sid,),
            ).fetchall():
                live_answered.append(
                    {
                        "id": q["id"],
                        "text": questions.render(c, q, live=True),
                        "answer": q["answer"],
                        "status": q["status"],
                    }
                )
            pacing = [
                dict(r) | {"clock": fmt_clock(r["t_s"])}
                for r in c.execute(
                    "SELECT t_s, decision, reason FROM pacing_log WHERE session_id=? ORDER BY id", (sid,)
                ).fetchall()
            ]
        t = work_time(s)
        return {
            "id": s["id"],
            "workflow_name": s["workflow_name"],
            "mode": s["mode"],
            "status": s["status"],
            "seeded": bool(s["script"]),
            "speed": s["speed"],
            "screen_share": bool(s["screen_share"]),
            "work_time_s": t,
            "clock": fmt_clock(t),
            "script_progress": (s["script_cursor"] / len(demo.SCRIPT_EVENTS)) if s["script"] else None,
            "script_complete": bool(s["script"]) and s["script_cursor"] >= len(demo.SCRIPT_EVENTS),
            "off_record": bool(s["off_record"]),
            "events": events,
            # Lock-In: the count is all the client ever gets while the session runs.
            "held_question_count": held,
            "questions_asked_during_session": asked_live,
            "live_question": live_q,
            "live_answered": live_answered,
            "pacing_log": pacing,
            "created_at": s["created_at"],
        }


def list_sessions() -> list[dict[str, Any]]:
    with tx() as c:
        rows = c.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
        return [
            {
                "id": r["id"],
                "workflow_name": r["workflow_name"],
                "mode": r["mode"],
                "status": r["status"],
                "seeded": bool(r["script"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def control(sid: str, action: str) -> dict[str, Any]:
    now = time.time()
    with tx() as c:
        materialize(c, sid)
        s = get_session_row(c, sid)
        st = s["status"]
        if action == "start":
            if st != "ready":
                raise HTTPException(409, "Session already started.")
            c.execute("UPDATE sessions SET status='active', started_at=? WHERE id=?", (now, sid))
            add_event(
                c,
                sid,
                0.0,
                "marker",
                "system",
                "Session started — Lock-In: observing quietly, all questions held until the end."
                if s["mode"] == "lockin"
                else "Session started — Live Coaching: brief questions only at natural pauses.",
            )
        elif action == "pause":
            if st != "active":
                raise HTTPException(409, "Only an active session can be paused.")
            c.execute("UPDATE sessions SET status='paused', paused_at=? WHERE id=?", (now, sid))
            add_event(
                c, sid, work_time(s, now), "marker", "system", "Paused by expert — nothing is observed while paused."
            )
        elif action == "resume":
            if st != "paused":
                raise HTTPException(409, "Session is not paused.")
            c.execute(
                "UPDATE sessions SET status='active', paused_total=paused_total+?, paused_at=NULL WHERE id=?",
                (now - s["paused_at"], sid),
            )
            add_event(c, sid, work_time(s, now), "marker", "system", "Resumed.")
        elif action == "advance":
            if st != "active" or not s["script"]:
                raise HTTPException(409, "Skipping ahead only applies to a running seeded demo session.")
            if s["script_cursor"] < len(demo.SCRIPT_EVENTS):
                gap = demo.SCRIPT_EVENTS[s["script_cursor"]]["t"] - work_time(s, now)
                if gap > 0:
                    c.execute("UPDATE sessions SET offset_s=offset_s+? WHERE id=?", (gap + 0.05, sid))
                materialize(c, sid)
        elif action == "end":
            if st not in ACTIVE:
                raise HTTPException(409, "Session is not running.")
            if st == "paused":
                c.execute(
                    "UPDATE sessions SET paused_total=paused_total+?, paused_at=NULL WHERE id=?",
                    (now - s["paused_at"], sid),
                )
                s = get_session_row(c, sid)
            if s["off_record"]:
                _close_off_record(c, s, work_time(s, now))
                s = get_session_row(c, sid)
            t_end = work_time(s, now)
            c.execute("UPDATE sessions SET status='debrief', ended_work_s=?, off_record=0 WHERE id=?", (t_end, sid))
            # Any live question still open is moved to the debrief — never dropped silently.
            c.execute("UPDATE questions SET status='deferred' WHERE session_id=? AND status='asked_live'", (sid,))
            add_event(c, sid, t_end, "marker", "system", "Session ended — moving to debrief.")
            if not s["script"]:
                _llm_custom_questions(c, get_session_row(c, sid))
            questions.apply_coverage(c, sid)
            mapbuilder.draft_from_session(c, sid)
        else:
            raise HTTPException(400, f"Unknown action {action}")
    return state(sid)


def discard(sid: str) -> None:
    with tx() as c:
        get_session_row(c, sid)
        c.execute("DELETE FROM nodes WHERE session_id=? AND status!='confirmed'", (sid,))
        c.execute("DELETE FROM sessions WHERE id=?", (sid,))


def _close_off_record(c: sqlite3.Connection, s: sqlite3.Row, t: float) -> None:
    since = s["off_record_since"] or 0.0
    add_event(
        c,
        s["id"],
        t,
        "marker",
        "system",
        f"Off the record {fmt_clock(since)}–{fmt_clock(t)} · nothing was captured or queued",
    )
    c.execute("UPDATE sessions SET off_record=0, off_record_since=NULL WHERE id=?", (s["id"],))


def set_off_record(sid: str, on: bool) -> dict[str, Any]:
    with tx() as c:
        materialize(c, sid)
        s = get_session_row(c, sid)
        if s["status"] not in ACTIVE:
            raise HTTPException(409, "Off-the-record applies to a running session.")
        t = work_time(s)
        if on and not s["off_record"]:
            c.execute("UPDATE sessions SET off_record=1, off_record_since=? WHERE id=?", (t, sid))
        elif not on and s["off_record"]:
            _close_off_record(c, s, t)
    return state(sid)


def strike_event(sid: str, event_id: str) -> dict[str, Any]:
    """Retroactively take a moment off the record: content is erased, dependent questions are dropped."""
    with tx() as c:
        s = get_session_row(c, sid)
        if s["status"] == "committed":
            raise HTTPException(409, "This session is already committed to the Work Map.")
        row = c.execute("SELECT * FROM events WHERE id=? AND session_id=?", (event_id, sid)).fetchone()
        if row is None:
            raise HTTPException(404, "Event not found.")
        d = loads(row["data"], {})
        c.execute(
            "UPDATE events SET text='Removed from the record by the expert', data=?, off_record=1 WHERE id=?",
            (dumps({"case": d.get("case"), "script_key": d.get("script_key")}), event_id),
        )
        c.execute(
            "DELETE FROM questions WHERE trigger_event_id=? AND status IN ('queued','deferred','asked_live')",
            (event_id,),
        )
        if s["status"] in FINISHED:
            mapbuilder.draft_from_session(c, sid)
    return state(sid)


def add_note(sid: str, text: str, kind: str = "note") -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise HTTPException(422, "Note is empty.")
    with tx() as c:
        materialize(c, sid)
        s = get_session_row(c, sid)
        if s["status"] not in ACTIVE:
            raise HTTPException(409, "Notes can be added while the session runs.")
        if s["off_record"]:
            raise HTTPException(409, "You are off the record — nothing is being captured.")
        last_case = None
        for r in c.execute("SELECT data FROM events WHERE session_id=? ORDER BY seq DESC", (sid,)).fetchall():
            last_case = loads(r["data"], {}).get("case")
            if last_case:
                break
        ev = add_event(c, sid, work_time(s), kind, "expert", text, "speaking", {"case": last_case})
        if not s["script"]:
            questions.queue_custom_gaps(c, sid, ev, workflow_skill_key(s))
    return state(sid)


def screen_signal(sid: str, kind: str, score: float | None, description: str | None) -> dict[str, Any]:
    """Client-side frame-diff signals. `idle` = screen stable and expert quiet → a natural pause."""
    with tx() as c:
        materialize(c, sid)
        s = get_session_row(c, sid)
        if s["status"] != "active" or s["off_record"]:
            return {"accepted": False}
        t = work_time(s)
        if kind == "change":
            text = description or f"Screen changed (frame difference {round((score or 0) * 100)}%) — no image stored"
            add_event(
                c,
                sid,
                t,
                "screen_change",
                "vision" if description else "observed",
                text,
                "navigating",
                {"score": score},
            )
        elif kind == "idle":
            add_event(c, sid, t, "pause", "observed", "Natural pause — screen stable and no speech", "idle", {})
            _maybe_ask_live(c, s, t, None)
    return {"accepted": True}


def answer_live(sid: str, qid: str, answer: str | None, defer: bool) -> dict[str, Any]:
    with tx() as c:
        s = get_session_row(c, sid)
        q = c.execute("SELECT * FROM questions WHERE id=? AND session_id=?", (qid, sid)).fetchone()
        if q is None or q["status"] != "asked_live":
            raise HTTPException(409, "That question is not awaiting an answer.")
        if defer or not (answer or "").strip():
            c.execute("UPDATE questions SET status='deferred' WHERE id=?", (qid,))
        else:
            c.execute(
                "UPDATE questions SET status='answered', answer=?, answered_at=? WHERE id=?",
                (answer.strip() if answer else "", now_iso(), qid),
            )
            add_event(
                c,
                sid,
                work_time(s),
                "transcript",
                "expert",
                answer.strip() if answer else "",
                "speaking",
                {"case": q["case_ref"], "answers": qid},
            )
    return state(sid)


def _llm_custom_questions(c: sqlite3.Connection, s: sqlite3.Row) -> None:
    """With a model configured, propose sharper gap questions for custom workflows (labelled model-generated)."""
    events = c.execute(
        "SELECT * FROM events WHERE session_id=? AND off_record=0 AND kind NOT IN ('marker') ORDER BY seq", (s["id"],)
    ).fetchall()
    if not events:
        return
    log = "\n".join(f"[{r['id']}] {fmt_clock(r['t_s'])} ({r['source']}) {r['text']}" for r in events)
    result = integrations.llm_json(
        "You are an apprentice learning an expert's workflow. Find what the screen alone cannot reveal: reasons, "
        "conditions that would change a decision, thresholds, exceptions, never-actions, escalation points.",
        f"Session log:\n{log}\n\nReturn a JSON list of at most 4 objects "
        '{"event_id": "...", "gap_type": "why|change_condition|threshold|exception|never|escalation", '
        '"question": "..."} — specific, cite the timestamp, no duplicates, nothing the expert already explained.',
    )
    if not isinstance(result, list):
        return
    ids = {r["id"]: r for r in events}
    for i, item in enumerate(result[:4]):
        if not isinstance(item, dict) or item.get("event_id") not in ids or not item.get("question"):
            continue
        gap = item.get("gap_type") if item.get("gap_type") in demo.GAP_WEIGHTS else "why"
        c.execute(
            """INSERT OR IGNORE INTO questions (id, session_id, key, gap_types, text, trigger_event_id, priority,
               status, targets, created_t_s) VALUES (?,?,?,?,?,?,?, 'queued', ?, ?)""",
            (
                new_id("q"),
                s["id"],
                f"llm-{i}",
                dumps([gap]),
                str(item["question"])[:400],
                item["event_id"],
                questions.priority_for([str(gap)], None, False, False) + 0.5,
                dumps({"skill": workflow_skill_key(s), "node": workflow_skill_key(s), "model_generated": True}),
                ids[item["event_id"]]["t_s"],
            ),
        )


# ---------------------------------------------------------------------------------------------------------------
# Debrief
# ---------------------------------------------------------------------------------------------------------------

DEBRIEF_TARGET = 5


def _q_public(c: sqlite3.Connection, q: sqlite3.Row) -> dict[str, Any]:
    trig = (
        c.execute("SELECT t_s, text, source FROM events WHERE id=?", (q["trigger_event_id"],)).fetchone()
        if q["trigger_event_id"]
        else None
    )
    return {
        "id": q["id"],
        "key": q["key"],
        "text": questions.render(c, q),
        "gap_types": loads(q["gap_types"], []),
        "priority": q["priority"],
        "status": q["status"],
        "answer": q["answer"],
        "phase": q["phase"],
        "evidence": {"clock": fmt_clock(trig["t_s"]), "text": trig["text"], "source": trig["source"]} if trig else None,
        "sample_answer": q["sample_answer"],
        "model_generated": bool(loads(q["targets"], {}).get("model_generated")),
        "generator": "model" if loads(q["targets"], {}).get("model_generated") else "deterministic",
    }


def debrief(sid: str) -> dict[str, Any]:
    with tx() as c:
        s = get_session_row(c, sid)
        if s["status"] not in FINISHED:
            # Lock-In: nothing about the questions exists for the client until the session ends.
            raise HTTPException(409, "The debrief opens when the session ends. Questions are held until then.")
        rows = c.execute("SELECT * FROM questions WHERE session_id=? ORDER BY priority DESC", (sid,)).fetchall()
        pending = [r for r in rows if r["status"] in ("queued", "deferred")]
        answered = [r for r in rows if r["status"] == "answered" and r["phase"] == "debrief"]
        skipped = [r for r in rows if r["status"] == "skipped"]
        answered_live = [r for r in rows if r["status"] == "answered" and r["phase"] == "live"]
        covered = [r for r in rows if r["status"] == "covered"]
        asked_debrief = len(answered) + len(skipped)
        target = min(DEBRIEF_TARGET, asked_debrief + len(pending))
        return {
            "session": {
                "id": s["id"],
                "workflow_name": s["workflow_name"],
                "mode": s["mode"],
                "status": s["status"],
                "seeded": bool(s["script"]),
            },
            "questions_asked_during_session": sum(1 for r in rows if r["phase"] == "live"),
            "held_during_session": len(rows) - len(answered_live),
            "covered": [{"text": questions.render(c, r), "reason": r["covered_reason"]} for r in covered],
            "answered_live": [_q_public(c, r) for r in answered_live],
            "current": _q_public(c, pending[0]) if pending and s["status"] == "debrief" else None,
            "progress": {"asked": asked_debrief, "target": target, "remaining": len(pending)},
            "can_finish": s["status"] == "debrief" and (asked_debrief >= target or not pending),
            "answered": [_q_public(c, r) for r in answered],
            "skipped": [_q_public(c, r) for r in skipped],
            "generator": "deterministic (demo fallback)"
            if not integrations.status()["llm"]["configured"]
            else "model + deterministic",
        }


def answer_debrief(sid: str, qid: str, answer: str | None, skip: bool) -> dict[str, Any]:
    with tx() as c:
        s = get_session_row(c, sid)
        if s["status"] != "debrief":
            raise HTTPException(409, "Debrief is not open.")
        q = c.execute("SELECT * FROM questions WHERE id=? AND session_id=?", (qid, sid)).fetchone()
        if q is None or q["status"] not in ("queued", "deferred"):
            raise HTTPException(409, "Question is not pending.")
        if skip or not (answer or "").strip():
            c.execute("UPDATE questions SET status='skipped', phase='debrief' WHERE id=?", (qid,))
        else:
            c.execute(
                "UPDATE questions SET status='answered', phase='debrief', answer=?, answered_at=? WHERE id=?",
                ((answer or "").strip(), now_iso(), qid),
            )
    return debrief(sid)


def finish_debrief(sid: str) -> dict[str, Any]:
    with tx() as c:
        s = get_session_row(c, sid)
        if s["status"] != "debrief":
            raise HTTPException(409, "Debrief is not open.")
        c.execute("UPDATE sessions SET status='review' WHERE id=?", (sid,))
        mapbuilder.generate_teachback(c, sid)
    return mapbuilder.teachback(sid)


def session_row_public(sid: str) -> dict[str, Any] | None:
    with tx() as c:
        return row_dict(c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone())
