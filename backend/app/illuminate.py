"""Illuminate — game-like onboarding grounded in the expert-confirmed Work Map.

Every unlock is explainable: a level opens only when the guardrails it teaches are expert-confirmed and its
prerequisite skills are mastered; mastery follows a visible rubric and stores the attempts behind it.
Practice replays are recorded but never change confirmed progress.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from . import curriculum as cur
from . import integrations, mapbuilder
from .db import dumps, loads, new_id, now_iso, tx
from .language import keywords

LEARNER = "learner-demo"


def _nodes() -> dict[str, dict[str, Any]]:
    return {n["key"]: n for n in mapbuilder.graph()["nodes"]}


def _mastery(learner: str) -> dict[str, dict[str, Any]]:
    with tx() as c:
        return {
            r["skill_key"]: {"status": r["status"], "evidence": loads(r["evidence"], {}), "updated_at": r["updated_at"]}
            for r in c.execute("SELECT * FROM mastery WHERE learner_id=?", (learner,)).fetchall()
        }


def _level(level_id: str) -> dict[str, Any]:
    for lv in cur.LEVELS:
        if lv["id"] == level_id:
            return lv
    raise HTTPException(404, "Level not found.")


def _scenario(sid: str) -> dict[str, Any]:
    if sid not in cur.SCENARIOS:
        raise HTTPException(404, "Scenario not found.")
    return cur.SCENARIOS[sid]


def level_state(
    lv: dict[str, Any], nodes: dict[str, dict[str, Any]], mastery: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    missing_confirm = [
        {
            "key": k,
            "title": nodes[k]["title"] if k in nodes else k,
            "status": nodes[k]["status"] if k in nodes else "not captured",
        }
        for k in lv["requires_confirmed"]
        if nodes.get(k, {}).get("status") != "confirmed"
    ]
    missing_prereq = [
        {"key": k, "title": nodes[k]["title"] if k in nodes else k}
        for k in lv["prereq_skills"]
        if mastery.get(k, {}).get("status") != "mastered"
    ]
    m = mastery.get(lv["skill"], {})
    if m.get("status") == "mastered":
        status = "mastered"
    elif missing_confirm:
        status = "awaiting_expert"
    elif missing_prereq:
        status = "locked"
    else:
        status = "practiced" if m.get("status") == "practiced" else "available"
    reasons = []
    if missing_confirm:
        reasons.append("Needs expert confirmation in the Work Map: " + ", ".join(x["title"] for x in missing_confirm))
    if missing_prereq:
        reasons.append("Master first: " + ", ".join(x["title"] for x in missing_prereq))
    return {
        "id": lv["id"],
        "order": lv["order"],
        "title": lv["title"],
        "subtitle": lv["subtitle"],
        "goal": lv["goal"],
        "skill": lv["skill"],
        "skill_title": nodes.get(lv["skill"], {}).get("title", lv["skill"]),
        "status": status,
        "lock_reasons": reasons,
        "missing_confirmation": missing_confirm,
        "missing_prereqs": missing_prereq,
        "prereq_skills": lv["prereq_skills"],
        "scenario_count": len(lv["scenarios"]),
        "mastery_evidence": m.get("evidence"),
    }


def overview(learner: str = LEARNER) -> dict[str, Any]:
    nodes = _nodes()
    mastery = _mastery(learner)
    levels = [level_state(lv, nodes, mastery) for lv in cur.LEVELS]
    confirmed_skills = [n for n in nodes.values() if n["type"] == "skill" and n["status"] == "confirmed"]
    return {
        "learner": learner,
        "levels": levels,
        "rubric": cur.RUBRIC,
        "tree": {
            "nodes": [
                {
                    "key": lv["skill"],
                    "title": nodes.get(lv["skill"], {}).get("title", lv["subtitle"]),
                    "level": lv["id"],
                    "status": st["status"],
                }
                for lv, st in zip(cur.LEVELS, levels, strict=True)
            ],
            "edges": [{"src": p, "dst": lv["skill"]} for lv in cur.LEVELS for p in lv["prereq_skills"]],
        },
        "map_ready": bool(confirmed_skills),
        "mastered": sum(1 for lv in levels if lv["status"] == "mastered"),
    }


def _public_scenario(sid: str) -> dict[str, Any]:
    sc = cur.SCENARIOS[sid]
    # The answer key never leaves the server before a decision is submitted.
    return {
        "id": sid,
        "title": sc["title"],
        "document": sc["document"],
        "prompt": sc["prompt"],
        "actions": sc["actions"],
        "reasons": sc["reasons"],
    }


def level_detail(level_id: str, learner: str = LEARNER) -> dict[str, Any]:
    lv = _level(level_id)
    nodes = _nodes()
    st = level_state(lv, nodes, _mastery(learner))
    if st["status"] in ("awaiting_expert", "locked"):
        return {"level": st, "scenarios": [], "rubric": cur.RUBRIC}
    return {
        "level": st,
        "scenarios": [_public_scenario(s) for s in lv["scenarios"]],
        "rubric": cur.RUBRIC,
        "skill_card": nodes.get(lv["skill"]),
    }


def _citations(node_key: str, cue_words: list[str], limit: int = 2) -> list[dict[str, Any]]:
    """Pick the expert-confirmed items on a node most relevant to this moment."""
    nodes = _nodes()
    n = nodes.get(node_key)
    if not n or n["status"] != "confirmed":
        return []
    items = []
    for field in mapbuilder.CARD_FIELDS:
        for it in n["card"].get(field, []):
            if not it.get("confirmed") or it.get("via"):
                continue
            hay = ((it.get("quote") or "") + " " + it["text"]).lower()
            score = sum(1 for w in cue_words if w.lower() in hay)
            clock = next((s.get("clock") for s in it.get("sources", []) if s.get("clock")), None)
            items.append(
                {
                    "score": score,
                    "node": node_key,
                    "node_title": n["title"],
                    "field": field,
                    "quote": it.get("quote"),
                    "text": it["text"],
                    "provenance": it["provenance"],
                    "clock": clock,
                }
            )
    items.sort(key=lambda x: -x["score"])
    return [i for i in items if i["score"] > 0][:limit] or items[:1]


def precheck(scenario_id: str, action_id: str, learner: str = LEARNER) -> dict[str, Any]:
    """Runs before submission. A consequential wrong choice triggers an intervention with confirmed reasoning."""
    sc = _scenario(scenario_id)
    _require_open(sc["level"], learner)
    rule = sc["consequential"].get(action_id)
    if not rule:
        return {"intervene": False}
    cites = _citations(rule["node"], rule["cite"])
    nodes = _nodes()
    msg = rule["lead"]
    if cites:
        q = cites[0]
        said = f"“{q['quote']}”" if q.get("quote") else q["text"]
        msg += f" Mira confirmed: {said}"
    llm = integrations.llm_text(
        "You are a warm, concise onboarding tutor. Use ONLY the confirmed expert knowledge given. Never invent rules.",
        f"Learner is about to submit '{action_id}' on: {sc['prompt']}\nConfirmed knowledge: "
        f"{[c['quote'] or c['text'] for c in cites]}\nWrite 2 sentences: flag the risk and point to the rule, then "
        "ask them to reconsider. Don't state the correct action outright.",
        200,
    )
    return {
        "intervene": True,
        "message": llm or msg,
        "generator": "model" if llm else "deterministic",
        "guardrail": {"key": rule["node"], "title": nodes.get(rule["node"], {}).get("title", rule["node"])},
        "citations": cites,
    }


def _require_open(level_id: str, learner: str) -> dict[str, Any]:
    st = level_state(_level(level_id), _nodes(), _mastery(learner))
    if st["status"] in ("awaiting_expert", "locked"):
        raise HTTPException(409, " ".join(st["lock_reasons"]) or "Level is locked.")
    return st


def submit(
    scenario_id: str,
    action_id: str,
    reason_id: str | None,
    path: list[dict[str, Any]],
    mode: str,
    learner: str = LEARNER,
) -> dict[str, Any]:
    sc = _scenario(scenario_id)
    if action_id not in {a["id"] for a in sc["actions"]}:
        raise HTTPException(422, "Unknown action.")
    _require_open(sc["level"], learner)
    interventions = sorted(
        {p["action_id"] for p in path if p.get("prechecked") and p.get("action_id") in sc["consequential"]}
    )
    action_ok = action_id == sc["correct_action"]
    reason_ok = reason_id == sc["correct_reason"]
    missed = [sc["consequential"][action_id]["node"]] if action_id in sc["consequential"] else []
    aid = new_id("att")
    with tx() as c:
        c.execute(
            """INSERT INTO attempts (id, learner_id, scenario_id, level_id, mode, path, interventions, action_id,
               reason_id, action_correct, reason_correct, guardrails_missed, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                aid,
                learner,
                scenario_id,
                sc["level"],
                mode,
                dumps(path),
                dumps(interventions),
                action_id,
                reason_id,
                int(action_ok),
                int(reason_ok),
                dumps(missed),
                now_iso(),
            ),
        )
    lv = _level(sc["level"])
    cites = _citations(
        next(iter(sc["consequential"].values()))["node"] if sc["consequential"] else lv["requires_confirmed"][0],
        [w for w in keywords(sc["explain"])][:8],
    )
    if mode == "learn":
        _update_mastery(lv, learner)
    nodes = _nodes()
    return {
        "attempt_id": aid,
        "action_correct": action_ok,
        "reason_correct": reason_ok,
        "guardrails_missed": [{"key": k, "title": nodes.get(k, {}).get("title", k)} for k in missed],
        "tutor_intervened": bool(interventions),
        "correct_action": next(a["label"] for a in sc["actions"] if a["id"] == sc["correct_action"]),
        "correct_reason": next(r["label"] for r in sc["reasons"] if r["id"] == sc["correct_reason"]),
        "explanation": sc["explain"],
        "citations": cites,
        "mode": mode,
        "level": level_state(lv, nodes, _mastery(learner)),
    }


def _update_mastery(lv: dict[str, Any], learner: str) -> None:
    with tx() as c:
        latest: dict[str, Any] = {}
        for r in c.execute(
            "SELECT * FROM attempts WHERE learner_id=? AND level_id=? AND mode='learn' ORDER BY created_at, rowid",
            (learner, lv["id"]),
        ).fetchall():
            latest[r["scenario_id"]] = r
        existing = c.execute(
            "SELECT status FROM mastery WHERE learner_id=? AND skill_key=?", (learner, lv["skill"])
        ).fetchone()
        if existing and existing["status"] == "mastered":
            return  # confirmed progress is never downgraded by later attempts
        if not latest:
            return
        done = [latest.get(s) for s in lv["scenarios"]]
        rubric = {
            "action": all(r is not None and r["action_correct"] for r in done),
            "reason": all(r is not None and r["reason_correct"] for r in done),
            "guardrails": all(r is not None and not loads(r["guardrails_missed"], []) for r in done),
            "independent": any(
                r is not None and not loads(r["interventions"], []) and r["action_correct"] for r in done
            ),
        }
        status = "mastered" if all(rubric.values()) else "practiced"
        evidence = {"rubric": rubric, "attempts": [r["id"] for r in done if r is not None], "decided_at": now_iso()}
        c.execute(
            """INSERT INTO mastery (learner_id, skill_key, status, evidence, updated_at) VALUES (?,?,?,?,?)
               ON CONFLICT(learner_id, skill_key) DO UPDATE SET status=excluded.status, evidence=excluded.evidence,
               updated_at=excluded.updated_at""",
            (learner, lv["skill"], status, dumps(evidence), now_iso()),
        )


def summary(level_id: str, learner: str = LEARNER) -> dict[str, Any]:
    lv = _level(level_id)
    nodes = _nodes()
    st = level_state(lv, nodes, _mastery(learner))
    with tx() as c:
        rows = c.execute(
            "SELECT * FROM attempts WHERE learner_id=? AND level_id=? ORDER BY created_at, rowid", (learner, level_id)
        ).fetchall()
    learn = {r["scenario_id"]: r for r in rows if r["mode"] == "learn"}
    scen = []
    missed: set[str] = set()
    for sid in lv["scenarios"]:
        sc = cur.SCENARIOS[sid]
        r = learn.get(sid)
        if r:
            missed.update(loads(r["guardrails_missed"], []))
        scen.append(
            {
                "id": sid,
                "title": sc["title"],
                "attempted": r is not None,
                "action_correct": bool(r and r["action_correct"]),
                "reason_correct": bool(r and r["reason_correct"]),
                "tutor_intervened": bool(r and loads(r["interventions"], [])),
                "chosen": next((a["label"] for a in sc["actions"] if r and a["id"] == r["action_id"]), None),
                "attempt_id": r["id"] if r else None,
                "at": r["created_at"] if r else None,
            }
        )
    rubric = (st.get("mastery_evidence") or {}).get("rubric") or {k["id"]: False for k in cur.RUBRIC}
    next_steps = []
    if not rubric.get("action"):
        next_steps.append("Replay the cases where your action differed from the expert's.")
    if not rubric.get("reason"):
        next_steps.append("Re-read the skill card's 'why' section — the reason matters as much as the action.")
    if not rubric.get("independent"):
        next_steps.append("Solve one case without the tutor stepping in.")
    if st["status"] == "mastered":
        unlocked = [l2["title"] for l2 in cur.LEVELS if lv["skill"] in l2["prereq_skills"]]
        why = "Mastered: every rubric line is met by the stored attempts below."
        if unlocked:
            why += " This lights the path to: " + ", ".join(unlocked) + "."
    else:
        unmet = [k["label"] for k in cur.RUBRIC if not rubric.get(k["id"])]
        why = "Not mastered yet — unmet: " + "; ".join(unmet) + "." if unmet else "Not attempted yet."
    return {
        "level": st,
        "rubric": [k | {"met": bool(rubric.get(k["id"]))} for k in cur.RUBRIC],
        "scenarios": scen,
        "demonstrated_skills": [nodes.get(lv["skill"], {}).get("title", lv["skill"])]
        if st["status"] == "mastered"
        else [],
        "missed_guardrails": [{"key": k, "title": nodes.get(k, {}).get("title", k)} for k in sorted(missed)],
        "practice_next": next_steps,
        "why": why,
        "practice_attempts": sum(1 for r in rows if r["mode"] == "practice"),
    }


def tutor(message: str, scenario_id: str | None, decided: bool) -> dict[str, Any]:
    """Coach with questions and confirmed knowledge only. If nothing confirmed applies, say so — never guess."""
    knowledge = mapbuilder.confirmed_knowledge()
    ctx = message
    sc = cur.SCENARIOS.get(scenario_id) if scenario_id else None
    if sc:
        ctx += " " + sc["prompt"] + " " + " ".join(str(v) for v in sc["document"].values())
    words = keywords(ctx)
    scored = []
    for k in knowledge:
        hay = keywords((k["quote"] or "") + " " + k["text"] + " " + k["node_title"])
        score = len(words & hay)
        if sc and k["node"] in (sc["consequential"] and [v["node"] for v in sc["consequential"].values()]):
            score += 2
        if score:
            scored.append((score, k))
    scored.sort(key=lambda x: -x[0])
    top = [k for _, k in scored[:2]]
    if not top:
        return {
            "reply": "I don't have expert-confirmed knowledge on that yet, so I won't guess. I've noted it as a "
            "question for Mira's next debrief.",
            "citations": [],
            "generator": "deterministic",
        }
    cites = [
        {
            "node": k["node"],
            "node_title": k["node_title"],
            "field": k["field"],
            "quote": k["quote"],
            "text": k["text"],
            "clock": next((s.get("clock") for s in k["sources"] if s.get("clock")), None),
        }
        for k in top
    ]
    llm = integrations.llm_text(
        "You are Umbra's onboarding tutor. Ground every statement in the confirmed expert knowledge provided; if it "
        "doesn't cover the question, say so. Coach Socratically: before the learner decides, ask a guiding question "
        "rather than giving the answer.",
        f"Learner: {message}\nDecided already: {decided}\nScenario: {sc['prompt'] if sc else 'none'}\n"
        f"Confirmed knowledge: {[c['quote'] or c['text'] for c in cites]}",
        250,
    )
    if llm:
        return {"reply": llm, "citations": cites, "generator": "model"}
    k = top[0]
    said = f"“{k['quote']}”" if k["quote"] else k["text"]
    reply = f"Here's what Mira confirmed in the Work Map: {said}"
    if sc and not decided:
        reply += f" Now look at this invoice — {sc['tutor_prompt']}"
    elif sc:
        reply += " That's the reasoning behind the expert's call on this case."
    return {"reply": reply, "citations": cites, "generator": "deterministic"}


def reset(learner: str = LEARNER) -> None:
    with tx() as c:
        c.execute("DELETE FROM attempts WHERE learner_id=?", (learner,))
        c.execute("DELETE FROM mastery WHERE learner_id=?", (learner,))
