"""Trial — recruiting assessment. No tutor, no hints, no corrective feedback, no answer leakage.

Output is evidence for a human reviewer: the candidate's full path, per-skill evidence and the rubric.
There is deliberately no aggregate score and no hire/reject recommendation.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException

from . import curriculum as cur
from . import mapbuilder
from .config import get_settings
from .db import dumps, loads, new_id, now_iso, tx

CONSENT_TEXT = [
    "You'll work through four fictional invoice cases. Take the action you think is right and explain why.",
    "We record only task-related evidence: your chosen action, your written rationale, the order of your choices "
    "and time spent per case. No camera, microphone, screen recording or personal profiling.",
    "There is no coaching, hint or feedback during the assessment — that's by design, so every candidate gets the "
    "same conditions.",
    "A person reviews your evidence against the visible rubric. Umbra makes no automated hire or reject decision "
    "and computes no overall score.",
    "Your responses are kept for {days} days and then deleted. You can view or delete them at any time with your "
    "receipt code.",
]


def _tasks_by_id() -> dict[str, dict[str, Any]]:
    return {t["id"]: t for t in cur.TRIAL_TASKS}


def _public_task(t: dict[str, Any]) -> dict[str, Any]:
    return {"id": t["id"], "title": t["title"], "document": t["document"], "actions": t["actions"], "skill": t["skill"]}


def _rubric() -> list[dict[str, Any]]:
    nodes = {n["key"]: n for n in mapbuilder.graph()["nodes"]}
    return [
        {
            "skill": k,
            "title": nodes.get(k, {}).get("title", k),
            "criterion": v,
            "ready": nodes.get(k, {}).get("status") == "confirmed",
        }
        for k, v in cur.TRIAL_RUBRIC_PUBLIC.items()
    ]


def brief() -> dict[str, Any]:
    rubric = _rubric()
    days = get_settings().candidate_retention_days
    return {
        "role": "Accounts Payable Clerk (fictional role at Halden Logistics GmbH)",
        "instructions": "For each case, choose the action you would take and write a short rationale.",
        "consent": [p.format(days=days) for p in CONSENT_TEXT],
        "retention_days": days,
        "rubric": rubric,
        "ready": all(r["ready"] for r in rubric),
        "task_count": len(cur.TRIAL_TASKS),
    }


def _candidate(c: Any, token: str) -> Any:
    r = c.execute("SELECT * FROM candidates WHERE token=?", (token,)).fetchone()
    if r is None:
        raise HTTPException(404, "No assessment found for this code (it may have been deleted).")
    return r


def start(alias: str, consent: bool) -> dict[str, Any]:
    if not consent:
        raise HTTPException(422, "Consent is required to start the assessment.")
    if not brief()["ready"]:
        raise HTTPException(409, "The rubric isn't ready: these skills need expert confirmation in the Work Map first.")
    alias = alias.strip()[:60] or "Candidate"
    cid, token = new_id("cand"), secrets.token_urlsafe(9)
    days = get_settings().candidate_retention_days
    with tx() as c:
        c.execute(
            """INSERT INTO candidates (id, token, alias, consent_at, status, started_at, retain_until)
               VALUES (?,?,?,?, 'in_progress', ?, ?)""",
            (
                cid,
                token,
                alias,
                now_iso(),
                now_iso(),
                (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="seconds"),
            ),
        )
    return {"token": token, "alias": alias}


def candidate_view(token: str) -> dict[str, Any]:
    with tx() as c:
        cand = _candidate(c, token)
        done = {
            r["task_id"]
            for r in c.execute("SELECT task_id FROM trial_responses WHERE candidate_id=?", (cand["id"],)).fetchall()
        }
        own = [
            dict(r) | {"path": loads(r["path"], [])}
            for r in c.execute(
                "SELECT task_id, action_id, gl_code, rationale, path, time_spent_s, created_at FROM trial_responses "
                "WHERE candidate_id=? ORDER BY created_at",
                (cand["id"],),
            ).fetchall()
        ]
    return {
        "alias": cand["alias"],
        "status": cand["status"],
        "retain_until": cand["retain_until"],
        "tasks": [_public_task(t) | {"submitted": t["id"] in done} for t in cur.TRIAL_TASKS],
        "rubric": _rubric(),
        "my_responses": own,
    }


def respond(
    token: str, task_id: str, action_id: str, rationale: str, path: list[dict[str, Any]], time_spent_s: float | None
) -> dict[str, Any]:
    task = _tasks_by_id().get(task_id)
    if task is None:
        raise HTTPException(404, "Unknown task.")
    if action_id not in {a["id"] for a in task["actions"]}:
        raise HTTPException(422, "Unknown action.")
    with tx() as c:
        cand = _candidate(c, token)
        if cand["status"] != "in_progress":
            raise HTTPException(409, "This assessment has already been submitted.")
        if c.execute(
            "SELECT 1 FROM trial_responses WHERE candidate_id=? AND task_id=?", (cand["id"], task_id)
        ).fetchone():
            raise HTTPException(409, "This case was already submitted.")
        c.execute(
            """INSERT INTO trial_responses (id, candidate_id, task_id, action_id, rationale, path, time_spent_s,
               created_at) VALUES (?,?,?,?,?,?,?,?)""",
            (
                new_id("tr"),
                cand["id"],
                task_id,
                action_id,
                rationale.strip()[:2000],
                dumps(path[:200]),
                time_spent_s,
                now_iso(),
            ),
        )
    # Neutral acknowledgement only: no correctness, no explanation, no hint.
    return {"recorded": True}


def finish(token: str) -> dict[str, Any]:
    with tx() as c:
        cand = _candidate(c, token)
        c.execute("UPDATE candidates SET status='submitted', submitted_at=? WHERE id=?", (now_iso(), cand["id"]))
    return {"submitted": True}


def delete_own(token: str) -> None:
    with tx() as c:
        cand = _candidate(c, token)
        c.execute("DELETE FROM candidates WHERE id=?", (cand["id"],))


# ---------------------------------------------------------------------------------------------------------------
# Reviewer console (requires the reviewer access code)
# ---------------------------------------------------------------------------------------------------------------


def require_reviewer(code: str | None) -> None:
    if not code or not secrets.compare_digest(code, get_settings().reviewer_access_code):
        raise HTTPException(403, "Reviewer access code required.")


def purge_expired() -> int:
    with tx() as c:
        cur_ = c.execute("DELETE FROM candidates WHERE retain_until < ?", (now_iso(),))
        return cur_.rowcount


def review_list() -> list[dict[str, Any]]:
    purge_expired()
    with tx() as c:
        rows = c.execute("SELECT * FROM candidates ORDER BY started_at DESC").fetchall()
        out = []
        for r in rows:
            n = c.execute("SELECT COUNT(*) FROM trial_responses WHERE candidate_id=?", (r["id"],)).fetchone()[0]
            out.append(
                {
                    "id": r["id"],
                    "alias": r["alias"],
                    "status": r["status"],
                    "started_at": r["started_at"],
                    "submitted_at": r["submitted_at"],
                    "retain_until": r["retain_until"],
                    "responses": n,
                    "of": len(cur.TRIAL_TASKS),
                }
            )
    return out


def _evidence_level(task: dict[str, Any], resp: dict[str, Any]) -> tuple[str, list[str]]:
    rationale = resp["rationale"].lower()
    cues = [w for w in task["cues"] if w.lower() in rationale]
    if resp["action_id"] != task["expected_action"]:
        return "not_demonstrated", cues
    return ("demonstrated" if cues else "partially_demonstrated"), cues


def review_detail(candidate_id: str) -> dict[str, Any]:
    nodes = {n["key"]: n for n in mapbuilder.graph()["nodes"]}
    with tx() as c:
        cand = c.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
        if cand is None:
            raise HTTPException(404, "Candidate not found (deleted or expired).")
        resps = {
            r["task_id"]: dict(r) | {"path": loads(r["path"], [])}
            for r in c.execute(
                "SELECT * FROM trial_responses WHERE candidate_id=? ORDER BY created_at", (candidate_id,)
            ).fetchall()
        }
    tasks = []
    for t in cur.TRIAL_TASKS:
        r = resps.get(t["id"])
        node = nodes.get(t["skill"], {})
        guardrails = [nodes[e] for e in _constraints(t["skill"]) if e in nodes]
        expert_rules = []
        for g in [node, *guardrails]:
            for field in ("thresholds", "never", "escalation", "exceptions", "why"):
                for it in (g.get("card") or {}).get(field, []):
                    if it.get("confirmed") and not it.get("via"):
                        expert_rules.append({"node": g["title"], "text": it.get("quote") or it["text"]})
        level, cues = _evidence_level(t, r) if r else ("not_assessed", [])
        tasks.append(
            {
                "task": _public_task(t),
                "skill_title": node.get("title", t["skill"]),
                "expected_action": next(a["label"] for a in t["actions"] if a["id"] == t["expected_action"]),
                "expert_rules": expert_rules[:4],
                "response": None
                if not r
                else {
                    "action": next(a["label"] for a in t["actions"] if a["id"] == r["action_id"]),
                    "rationale": r["rationale"],
                    "path": r["path"],
                    "time_spent_s": r["time_spent_s"],
                    "submitted_at": r["created_at"],
                },
                "evidence_level": level,
                "matched_cues": cues,
            }
        )
    return {
        "candidate": {
            "id": cand["id"],
            "alias": cand["alias"],
            "status": cand["status"],
            "consent_at": cand["consent_at"],
            "retain_until": cand["retain_until"],
        },
        "tasks": tasks,
        "rubric": _rubric(),
        "notice": "Evidence for human review only. Umbra computes no overall score and makes no hire/reject "
        "recommendation. Cue matching is an assistive signal — read the rationale.",
    }


def _constraints(skill: str) -> list[str]:
    g = mapbuilder.graph()
    return [e["dst"] for e in g["edges"] if e["src"] == skill and e["type"] == "constrained_by"]


def review_delete(candidate_id: str) -> None:
    with tx() as c:
        c.execute("DELETE FROM candidates WHERE id=?", (candidate_id,))
