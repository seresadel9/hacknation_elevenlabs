"""Work Map construction: draft nodes from observation → teach-back → expert-confirmed knowledge graph.

Status ladder (drives the dim → lit visual): draft → needs_confirmation → confirmed.
Provenance is tracked per item: observed | expert_statement | ai_inference. An inference is never shown as a quote.
Uncertain statements are never confirmed: they are kept as open questions on the card.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException

from . import demo_script as demo
from . import integrations
from .db import dumps, loads, new_id, now_iso, tx
from .language import classify_sentence, fmt_clock, is_uncertain, split_sentences, to_apprentice_voice

FIELD_FOR = {
    "never": "never",
    "threshold": "thresholds",
    "escalation": "escalation",
    "exception": "exceptions",
    "why": "why",
    "how": "how",
}
CARD_FIELDS = ("how", "why", "thresholds", "exceptions", "escalation", "never", "observations")
STATUS_RANK = {"draft": 0, "needs_confirmation": 1, "confirmed": 2}


def _empty_card() -> dict[str, Any]:
    return {f: [] for f in CARD_FIELDS} | {"meaning": None, "when": None, "evidence": [], "open_questions": []}


def _get_node(c: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    r = c.execute("SELECT * FROM nodes WHERE key=?", (key,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["card"] = loads(d["card"], {}) or _empty_card()
    return d


def _save_node(c: sqlite3.Connection, n: dict[str, Any]) -> None:
    c.execute(
        """INSERT INTO nodes (key, type, title, summary, status, card, session_id, seeded, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(key) DO UPDATE SET title=excluded.title, summary=excluded.summary, status=excluded.status,
             card=excluded.card, updated_at=excluded.updated_at""",
        (
            n["key"],
            n["type"],
            n["title"],
            n.get("summary", ""),
            n["status"],
            dumps(n["card"]),
            n.get("session_id"),
            int(n.get("seeded", 0)),
            now_iso(),
        ),
    )


def _add_edge(c: sqlite3.Connection, src: str, dst: str, etype: str, provenance: str = "ai_inference") -> None:
    if src == dst:
        return
    if (
        c.execute("SELECT 1 FROM nodes WHERE key=?", (src,)).fetchone()
        and c.execute("SELECT 1 FROM nodes WHERE key=?", (dst,)).fetchone()
    ):
        c.execute(
            "INSERT OR IGNORE INTO edges (src, dst, type, provenance) VALUES (?,?,?,?)", (src, dst, etype, provenance)
        )


def _raise_status(n: dict[str, Any], status: str) -> None:
    if STATUS_RANK[status] > STATUS_RANK[n["status"]]:
        n["status"] = status


def _ensure_node(
    c: sqlite3.Connection, key: str, sid: str, seeded: bool, fallback: dict[str, Any] | None = None
) -> dict[str, Any]:
    n = _get_node(c, key)
    if n is not None:
        return n
    spec = demo.NODE_CATALOG.get(key) or fallback or {"type": "skill", "title": key, "summary": ""}
    card = _empty_card()
    if spec.get("meaning"):
        card["meaning"] = {"text": spec["meaning"], "provenance": "ai_inference", "confirmed": False}
    if spec.get("when"):
        card["when"] = {"text": spec["when"], "provenance": "ai_inference", "confirmed": False}
    for step in spec.get("how", []):
        card["how"].append({"text": step, "provenance": "observed", "confirmed": False, "sources": []})
    n = {
        "key": key,
        "type": spec["type"],
        "title": spec["title"],
        "summary": spec.get("summary", ""),
        "status": "draft",
        "card": card,
        "session_id": sid,
        "seeded": int(seeded),
    }
    _save_node(c, n)
    return n


def draft_from_session(c: sqlite3.Connection, sid: str) -> None:
    """Turn captured (non-redacted) moments into DRAFT nodes. Re-runnable: rebuilds this session's drafts."""
    s = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    seeded = bool(s["script"])
    c.execute("DELETE FROM nodes WHERE session_id=? AND status='draft'", (sid,))
    events = c.execute("SELECT * FROM events WHERE session_id=? AND off_record=0 ORDER BY seq", (sid,)).fetchall()

    if not seeded:
        from .capture import workflow_skill_key  # local import: capture imports this module

        skill_key = workflow_skill_key(s)
        _ensure_node(
            c,
            skill_key,
            sid,
            False,
            {
                "type": "skill",
                "title": s["workflow_name"],
                "summary": "Captured from an expert session (custom workflow).",
            },
        )
    for ev in events:
        data = loads(ev["data"], {})
        refs: list[str] = list(data.get("refs", []))
        if not seeded and ev["kind"] in ("note", "transcript", "screen_change") and ev["source"] != "system":
            dkey = f"d-{ev['id']}"
            _ensure_node(
                c,
                dkey,
                sid,
                False,
                {
                    "type": "decision" if ev["kind"] != "screen_change" else "step",
                    "title": ev["text"][:70] + ("…" if len(ev["text"]) > 70 else ""),
                    "summary": ev["text"],
                },
            )
            refs.append(dkey)
            _add_edge(c, skill_key, dkey, "demonstrated_by")
        if not refs:
            continue
        evidence_key = None
        if ev["kind"] in ("decision", "note", "transcript"):
            evidence_key = f"ev-{ev['id']}"
            _ensure_node(
                c,
                evidence_key,
                sid,
                seeded,
                {
                    "type": "evidence",
                    "title": f"{fmt_clock(ev['t_s'])} · {'Expert said' if ev['source'] == 'expert' else 'Observed'}",
                    "summary": ev["text"],
                },
            )
        for key in refs:
            n = _ensure_node(c, key, sid, seeded)
            entry = {
                "event_id": ev["id"],
                "session_id": sid,
                "clock": fmt_clock(ev["t_s"]),
                "text": ev["text"],
                "kind": "expert_statement" if ev["source"] == "expert" else "observed",
                "simulated": ev["source"] == "simulated",
            }
            n["card"]["evidence"] = [e for e in n["card"]["evidence"] if e.get("event_id") != ev["id"]] + [entry]
            _save_node(c, n)
            if evidence_key and n["type"] in ("decision", "guardrail"):
                _add_edge(c, key, evidence_key, "supported_by_evidence", "observed")
    if seeded:
        for src, dst, etype in demo.EDGE_CATALOG:
            _add_edge(c, src, dst, etype)


# ---------------------------------------------------------------------------------------------------------------
# Teach-back
# ---------------------------------------------------------------------------------------------------------------


def _parts_from_answer(answer: str) -> tuple[list[dict[str, Any]], str]:
    """Split an answer into card-ready parts. Uses a model when configured; deterministic otherwise."""
    llm = integrations.llm_json(
        "You are an apprentice repeating back what an expert told you, in your own words, without adding facts.",
        "Expert answer:\n" + answer + "\n\nReturn a JSON list of objects "
        '{"quote": "<exact sentence from the answer>", "field": "how|why|thresholds|exceptions|escalation|never", '
        '"paraphrase": "<your restatement, second person>", "uncertain": true|false}. Mark uncertain whenever '
        "the expert hedges.",
    )
    if isinstance(llm, list) and llm and all(isinstance(p, dict) and p.get("quote") for p in llm):
        parts = []
        for p in llm:
            uncertain = bool(p.get("uncertain")) or is_uncertain(str(p["quote"]))
            field = p.get("field") if p.get("field") in FIELD_FOR.values() else "how"
            parts.append(
                {
                    "field": "uncertain" if uncertain else field,
                    "quote": str(p["quote"]),
                    "text": str(p.get("paraphrase") or p["quote"]),
                    "uncertain": uncertain,
                }
            )
        return parts, "llm"
    parts = []
    for sentence in split_sentences(answer):
        cls = classify_sentence(sentence)
        parts.append(
            {
                "field": "uncertain" if cls == "uncertain" else FIELD_FOR.get(cls, "how"),
                "quote": sentence,
                "text": to_apprentice_voice(sentence),
                "uncertain": cls == "uncertain",
            }
        )
    return parts, "deterministic"


def _summarise(parts: list[dict[str, Any]]) -> tuple[str, list[str], str]:
    sure = [p for p in parts if not p["uncertain"]]
    unresolved = [p["quote"] for p in parts if p["uncertain"]]
    if not sure:
        return "I couldn't extract anything certain from this answer.", unresolved, "low"
    text = "Here's what I understood: " + " ".join(p["text"].rstrip(".") + "." for p in sure)
    return text, unresolved, "high" if not unresolved else "medium"


def generate_teachback(c: sqlite3.Connection, sid: str) -> None:
    c.execute("DELETE FROM teachback_items WHERE session_id=?", (sid,))
    s = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    seq = 0

    def add(
        node_key: str,
        kind: str,
        text: str,
        provenance: str,
        generator: str,
        sources: list[dict[str, Any]],
        parts: list[dict[str, Any]],
        confidence: str,
        unresolved: list[str],
    ) -> None:
        nonlocal seq
        seq += 1
        c.execute(
            """INSERT INTO teachback_items (id, session_id, seq, node_key, kind, text, original_text, provenance,
               generator, sources, parts, confidence, unresolved) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                new_id("tb"),
                sid,
                seq,
                node_key,
                kind,
                text,
                text,
                provenance,
                generator,
                dumps(sources),
                dumps(parts),
                confidence,
                dumps(unresolved),
            ),
        )

    events = c.execute("SELECT * FROM events WHERE session_id=? AND off_record=0 ORDER BY seq", (sid,)).fetchall()
    captured: dict[str, list[sqlite3.Row]] = {}
    for ev in events:
        for ref in loads(ev["data"], {}).get("refs", []):
            captured.setdefault(ref, []).append(ev)

    if s["script"]:
        steps = [k for k in demo.NODE_CATALOG if k.startswith("step-") and k in captured]
        if steps:
            add(
                "workflow",
                "workflow",
                "The workflow I observed: " + " → ".join(demo.NODE_CATALOG[k]["title"] for k in steps) + ".",
                "ai_inference",
                "deterministic",
                [{"clock": fmt_clock(captured[k][0]["t_s"]), "text": captured[k][0]["text"]} for k in steps[:3]],
                [
                    {
                        "field": "step",
                        "node": k,
                        "text": demo.NODE_CATALOG[k]["title"],
                        "quote": None,
                        "uncertain": False,
                    }
                    for k in steps
                ],
                "high",
                [],
            )
        for dkey, inf in demo.DECISION_INFERENCES.items():
            if dkey not in captured:
                continue
            ev = next(e for e in captured[dkey] if e["kind"] == "decision")
            add(
                dkey,
                "observed_decision",
                inf["text"],
                "ai_inference",
                "deterministic",
                [{"event_id": ev["id"], "clock": fmt_clock(ev["t_s"]), "text": ev["text"], "kind": "observed"}],
                [{"field": "how", "skill": inf["skill"], "text": inf["text"], "quote": None, "uncertain": False}],
                "medium",
                [],
            )
    else:
        for ev in events:
            if (
                ev["kind"] in ("note", "transcript")
                and ev["source"] == "expert"
                and not loads(ev["data"], {}).get("answers")
            ):
                text = "I noted that at " + fmt_clock(ev["t_s"]) + ": " + to_apprentice_voice(ev["text"])
                add(
                    f"d-{ev['id']}",
                    "observed_decision",
                    text,
                    "ai_inference",
                    "deterministic",
                    [
                        {
                            "event_id": ev["id"],
                            "clock": fmt_clock(ev["t_s"]),
                            "text": ev["text"],
                            "kind": "expert_statement",
                        }
                    ],
                    [
                        {
                            "field": "how",
                            "text": to_apprentice_voice(ev["text"]),
                            "quote": ev["text"],
                            "uncertain": False,
                        }
                    ],
                    "medium",
                    [],
                )

    qs = c.execute("SELECT * FROM questions WHERE session_id=? ORDER BY priority DESC", (sid,)).fetchall()
    from .questions import render

    for q in qs:
        targets = loads(q["targets"], {})
        node = targets.get("node") or targets.get("skill")
        trig = c.execute("SELECT * FROM events WHERE id=?", (q["trigger_event_id"],)).fetchone()
        sources = []
        if trig:
            sources.append(
                {
                    "event_id": trig["id"],
                    "clock": fmt_clock(trig["t_s"]),
                    "text": trig["text"],
                    "kind": "observed" if trig["source"] != "expert" else "expert_statement",
                }
            )
        if q["status"] == "answered":
            parts, generator = _parts_from_answer(q["answer"] or "")
            for p in parts:
                p["skill"] = targets.get("skill")
            text, unresolved, confidence = _summarise(parts)
            sources.append(
                {
                    "question_id": q["id"],
                    "question": render(c, q),
                    "text": q["answer"],
                    "kind": "expert_statement",
                    "phase": q["phase"],
                }
            )
            add(node, "expert_answer", text, "ai_inference", generator, sources, parts, confidence, unresolved)
        elif q["status"] in ("skipped", "queued", "deferred"):
            add(
                node,
                "open_question",
                "Still unanswered: " + render(c, q),
                "ai_inference",
                "deterministic",
                sources,
                [],
                "low",
                [render(c, q)],
            )


def _item_public(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    for f in ("sources", "parts", "unresolved"):
        d[f] = loads(d[f], [])
    d["confirmable"] = d["kind"] != "open_question" and any(not p.get("uncertain") for p in d["parts"])
    return d


def teachback(sid: str) -> dict[str, Any]:
    with tx() as c:
        s = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if s is None:
            raise HTTPException(404, "Session not found.")
        if s["status"] not in ("review", "committed"):
            raise HTTPException(409, "The teach-back is generated when the debrief is finished.")
        items = [
            _item_public(r)
            for r in c.execute("SELECT * FROM teachback_items WHERE session_id=? ORDER BY seq", (sid,)).fetchall()
        ]
        return {
            "session": {
                "id": s["id"],
                "workflow_name": s["workflow_name"],
                "status": s["status"],
                "mode": s["mode"],
                "seeded": bool(s["script"]),
            },
            "items": items,
            "generator": "model" if integrations.status()["llm"]["configured"] else "deterministic (demo fallback)",
        }


def update_item(item_id: str, status: str, text: str | None) -> dict[str, Any]:
    with tx() as c:
        r = c.execute("SELECT * FROM teachback_items WHERE id=?", (item_id,)).fetchone()
        if r is None:
            raise HTTPException(404, "Teach-back item not found.")
        s = c.execute("SELECT status FROM sessions WHERE id=?", (r["session_id"],)).fetchone()
        if s["status"] != "review":
            raise HTTPException(409, "This teach-back is already committed.")
        item = _item_public(r)
        if status == "edited":
            if not (text or "").strip():
                raise HTTPException(422, "Edited text is empty.")
            parts = []
            for sentence in split_sentences(text or ""):
                cls = classify_sentence(sentence)
                parts.append(
                    {
                        "field": "uncertain" if cls == "uncertain" else FIELD_FOR.get(cls, "how"),
                        "quote": sentence,
                        "text": sentence,
                        "uncertain": cls == "uncertain",
                        "skill": (item["parts"][0].get("skill") if item["parts"] else None),
                    }
                )
            if item["kind"] == "workflow":
                parts = item["parts"]
            unresolved = [p["quote"] for p in parts if p["uncertain"]]
            if not any(not p["uncertain"] for p in parts):
                raise HTTPException(422, "Every sentence in the edit is uncertain — it cannot be confirmed.")
            c.execute(
                """UPDATE teachback_items SET status='edited', text=?, provenance='expert_statement', parts=?,
                   unresolved=?, confidence=? WHERE id=?""",
                (
                    (text or "").strip(),
                    dumps(parts),
                    dumps(unresolved),
                    "high" if not unresolved else "medium",
                    item_id,
                ),
            )
        elif status == "confirmed":
            if not item["confirmable"]:
                raise HTTPException(422, "Uncertain or unanswered knowledge cannot be confirmed.")
            c.execute("UPDATE teachback_items SET status='confirmed' WHERE id=?", (item_id,))
        elif status in ("rejected", "pending"):
            c.execute("UPDATE teachback_items SET status=?, text=original_text WHERE id=?", (status, item_id))
        else:
            raise HTTPException(400, "Unknown status.")
        return _item_public(c.execute("SELECT * FROM teachback_items WHERE id=?", (item_id,)).fetchone())


def commit(sid: str) -> dict[str, Any]:
    """Write reviewed teach-back items into the Work Map. Only confirmed/edited items light nodes up."""
    with tx() as c:
        s = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if s is None:
            raise HTTPException(404, "Session not found.")
        if s["status"] != "review":
            raise HTTPException(409, "Finish the debrief before committing.")
        items = [
            _item_public(r)
            for r in c.execute("SELECT * FROM teachback_items WHERE session_id=? ORDER BY seq", (sid,)).fetchall()
        ]
        lit: list[str] = []
        for item in items:
            ok = item["status"] in ("confirmed", "edited")
            prov = "expert_statement" if item["status"] == "edited" else None
            if item["kind"] == "workflow":
                for p in item["parts"]:
                    n = _get_node(c, p["node"])
                    if n and ok:
                        _raise_status(n, "confirmed")
                        _save_node(c, n)
                        lit.append(n["key"])
                continue
            node = _get_node(c, item["node_key"]) or _ensure_node(c, item["node_key"], sid, bool(s["script"]))
            skill_keys = {p.get("skill") for p in item["parts"] if p.get("skill")}
            skills = [n for n in (_get_node(c, k) for k in skill_keys if k and k != node["key"]) if n]

            if item["kind"] == "open_question":
                for n in [node, *skills]:
                    n["card"]["open_questions"].append(
                        {
                            "text": item["unresolved"][0] if item["unresolved"] else item["text"],
                            "reason": "Not answered in the debrief",
                            "session_id": sid,
                        }
                    )
                    _raise_status(n, "needs_confirmation")
                    _save_node(c, n)
                continue
            if not ok:
                for n in [node, *skills]:
                    _raise_status(n, "needs_confirmation")
                    if item["status"] == "rejected":
                        n["card"]["open_questions"].append(
                            {
                                "text": item["original_text"],
                                "reason": "Teach-back rejected by the expert",
                                "session_id": sid,
                            }
                        )
                    _save_node(c, n)
                continue

            for p in item["parts"]:
                if p["uncertain"]:
                    for n in [node, *skills]:
                        n["card"]["open_questions"].append(
                            {"text": p["quote"], "reason": "Expert was unsure — not confirmed", "session_id": sid}
                        )
                    continue
                entry = {
                    "text": p["text"],
                    "quote": p.get("quote"),
                    "provenance": prov or ("expert_statement" if p.get("quote") else "ai_inference"),
                    "paraphrase_by": None if prov else item["generator"],
                    "confirmed": True,
                    "sources": item["sources"],
                    "session_id": sid,
                }
                field = p["field"] if p["field"] in CARD_FIELDS else "how"
                if item["kind"] == "observed_decision":
                    node["card"]["observations"].append(entry | {"provenance": prov or "ai_inference"})
                    for sk in skills:
                        sk["card"]["how"].append(entry | {"provenance": prov or "ai_inference", "via": node["key"]})
                else:
                    node["card"][field].append(entry)
                    for sk in skills:
                        sk["card"][field].append(entry | {"via": node["key"]})
            for n in [node, *skills]:
                for f in ("meaning", "when"):
                    if n["card"].get(f):
                        n["card"][f]["confirmed"] = True
                _raise_status(n, "confirmed")
                _save_node(c, n)
                lit.append(n["key"])
            # Evidence moments behind confirmed knowledge light up too; expert answers become evidence nodes.
            for src in item["sources"]:
                if src.get("event_id"):
                    ev_node = _get_node(c, f"ev-{src['event_id']}")
                    if ev_node:
                        _raise_status(ev_node, "confirmed")
                        _save_node(c, ev_node)
                        lit.append(ev_node["key"])
                        _add_edge(c, node["key"], ev_node["key"], "supported_by_evidence", "observed")
                if src.get("question_id"):
                    ekey = f"ev-ans-{src['question_id']}"
                    ev_node = _ensure_node(
                        c,
                        ekey,
                        sid,
                        bool(s["script"]),
                        {"type": "evidence", "title": "Debrief · expert statement", "summary": src["text"]},
                    )
                    ev_node["card"]["evidence"] = [
                        {
                            "kind": "expert_statement",
                            "text": src["text"],
                            "question": src.get("question"),
                            "session_id": sid,
                        }
                    ]
                    _raise_status(ev_node, "confirmed")
                    _save_node(c, ev_node)
                    lit.append(ekey)
                    _add_edge(c, node["key"], ekey, "supported_by_evidence", "expert_statement")
            if node["type"] == "decision":
                for case in c.execute(
                    "SELECT dst FROM edges WHERE src=? AND type='demonstrated_by'", (node["key"],)
                ).fetchall():
                    cn = _get_node(c, case["dst"])
                    if cn:
                        _raise_status(cn, "confirmed")
                        _save_node(c, cn)
                        lit.append(cn["key"])
        c.execute("UPDATE sessions SET status='committed' WHERE id=?", (sid,))
    return {"lit": sorted(set(lit)), "graph": graph()}


# ---------------------------------------------------------------------------------------------------------------
# Graph queries
# ---------------------------------------------------------------------------------------------------------------


def _node_public(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["card"] = loads(d["card"], {})
    d["seeded"] = bool(d["seeded"])
    return d


def graph() -> dict[str, Any]:
    with tx() as c:
        nodes = [_node_public(r) for r in c.execute("SELECT * FROM nodes ORDER BY type, key").fetchall()]
        edges = [dict(r) for r in c.execute("SELECT * FROM edges ORDER BY id").fetchall()]
    counts = {st: sum(1 for n in nodes if n["status"] == st) for st in STATUS_RANK}
    return {"nodes": nodes, "edges": edges, "counts": counts}


def node_detail(key: str) -> dict[str, Any]:
    with tx() as c:
        r = c.execute("SELECT * FROM nodes WHERE key=?", (key,)).fetchone()
        if r is None:
            raise HTTPException(404, "Node not found.")
        node = _node_public(r)
        rels = []
        for e in c.execute("SELECT * FROM edges WHERE src=? OR dst=?", (key, key)).fetchall():
            other = e["dst"] if e["src"] == key else e["src"]
            o = c.execute("SELECT key, type, title, status FROM nodes WHERE key=?", (other,)).fetchone()
            if o:
                rels.append({"type": e["type"], "direction": "out" if e["src"] == key else "in", "node": dict(o)})
        node["relations"] = rels
        return node


def confirmed_knowledge() -> list[dict[str, Any]]:
    """Every expert-confirmed card item, flattened — the only material the tutor may ground on."""
    out = []
    for n in graph()["nodes"]:
        if n["status"] != "confirmed":
            continue
        for field in CARD_FIELDS:
            for item in n["card"].get(field, []):
                if item.get("confirmed") and not item.get("via"):
                    out.append(
                        {
                            "node": n["key"],
                            "node_title": n["title"],
                            "node_type": n["type"],
                            "field": field,
                            "text": item["text"],
                            "quote": item.get("quote"),
                            "sources": item.get("sources", []),
                        }
                    )
    return out
