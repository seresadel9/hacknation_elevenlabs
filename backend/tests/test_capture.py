"""Capture, Lock-In invariants, debrief and Work Map confirmation."""

from app import demo_script as demo
from app.db import tx


def _run_to_end(client, mode="lockin"):
    sid = client.post("/api/sessions", json={"mode": mode, "use_demo_script": True}).json()["id"]
    client.post(f"/api/sessions/{sid}/control", json={"action": "start"})
    return sid


def _jump_to_end(sid):
    with tx() as c:
        c.execute("UPDATE sessions SET offset_s=? WHERE id=?", (demo.SCRIPT_END_T + 1, sid))


def test_lockin_never_reveals_questions_during_session(client):
    sid = _run_to_end(client)
    _jump_to_end(sid)
    st = client.get(f"/api/sessions/{sid}").json()
    assert st["held_question_count"] >= 3
    assert st["live_question"] is None
    assert st["questions_asked_during_session"] == 0
    body = str(st)
    for spec in demo.GAPS.values():
        assert spec["text"][:30] not in body
        assert spec["sample_answer"][:30] not in body
    # Debrief is closed while the session runs.
    assert client.get(f"/api/sessions/{sid}/debrief").status_code == 409


def test_debrief_asks_at_least_three_specific_unanswered_questions(client):
    sid = _run_to_end(client)
    _jump_to_end(sid)
    client.post(f"/api/sessions/{sid}/control", json={"action": "end"})
    d = client.get(f"/api/sessions/{sid}/debrief").json()
    assert d["questions_asked_during_session"] == 0
    # The "why" behind the Kessler recode was already said aloud at 02:21 — it must not be asked again.
    assert any("already said" in c["reason"] for c in d["covered"])
    asked = []
    while d["current"]:
        q = d["current"]
        assert q["evidence"] and q["evidence"]["clock"]
        assert q["key"] not in {x["key"] for x in asked}
        asked.append(q)
        d = client.post(
            f"/api/sessions/{sid}/debrief/answer", json={"question_id": q["id"], "answer": q["sample_answer"]}
        ).json()
    assert d["progress"]["asked"] >= 3
    assert asked[0]["key"] == "q-atlas-never"  # highest risk first
    assert "q-kessler-why" not in {q["key"] for q in asked}


def test_teachback_and_commit_light_up_graph_but_not_uncertain(client):
    sid = _run_to_end(client)
    _jump_to_end(sid)
    client.post(f"/api/sessions/{sid}/control", json={"action": "end"})
    g = client.get("/api/graph").json()
    assert g["nodes"] and all(n["status"] == "draft" for n in g["nodes"])
    d = client.get(f"/api/sessions/{sid}/debrief").json()
    while d["current"]:
        q = d["current"]
        d = client.post(
            f"/api/sessions/{sid}/debrief/answer", json={"question_id": q["id"], "answer": q["sample_answer"]}
        ).json()
    tb = client.post(f"/api/sessions/{sid}/debrief/finish").json()
    items = tb["items"]
    scope = next(i for i in items if "software licences" in str(i["unresolved"]))
    assert scope["confidence"] == "medium"
    for i in items:
        if i["confirmable"]:
            assert client.patch(f"/api/teachback/{i['id']}", json={"status": "confirmed"}).status_code == 200
    res = client.post(f"/api/sessions/{sid}/commit").json()
    nodes = {n["key"]: n for n in res["graph"]["nodes"]}
    g = nodes["g-capex-5000"]
    assert g["status"] == "confirmed"
    assert any(t.get("quote", "").startswith("Per item, net of VAT") for t in g["card"]["thresholds"])
    # The hedge about software licences is surfaced, never confirmed.
    assert any("software licences" in q["text"] for q in g["card"]["open_questions"])
    assert not any(
        "software licences" in (t.get("quote") or "") for f in ("how", "thresholds", "exceptions") for t in g["card"][f]
    )
    # Typed relationships exist.
    types = {e["type"] for e in res["graph"]["edges"]}
    assert {
        "prerequisite_for",
        "depends_on",
        "demonstrated_by",
        "constrained_by",
        "exception_to",
        "supported_by_evidence",
    } <= types


def test_all_uncertain_item_cannot_be_confirmed(client):
    sid = _run_to_end(client)
    _jump_to_end(sid)
    client.post(f"/api/sessions/{sid}/control", json={"action": "end"})
    d = client.get(f"/api/sessions/{sid}/debrief").json()
    client.post(
        f"/api/sessions/{sid}/debrief/answer",
        json={"question_id": d["current"]["id"], "answer": "Honestly I'm not sure, maybe."},
    )
    tb = client.post(f"/api/sessions/{sid}/debrief/finish").json()
    item = next(i for i in tb["items"] if i["kind"] == "expert_answer")
    assert not item["confirmable"]
    assert client.patch(f"/api/teachback/{item['id']}", json={"status": "confirmed"}).status_code == 422


def test_off_record_drops_events_and_strike_removes_questions(client):
    sid = _run_to_end(client)
    client.post(f"/api/sessions/{sid}/off-record", json={"on": True})
    _jump_to_end(sid)
    st = client.post(f"/api/sessions/{sid}/off-record", json={"on": False}).json()
    assert st["held_question_count"] == 0
    assert any("Off the record" in e["text"] for e in st["events"])
    assert not any("Kessler" in e["text"] for e in st["events"])


def test_strike_event(client):
    sid = _run_to_end(client)
    _jump_to_end(sid)
    st = client.get(f"/api/sessions/{sid}").json()
    atlas = next(e for e in st["events"] if "Forwarded INV-4475" in e["text"])
    before = st["held_question_count"]
    st = client.post(f"/api/sessions/{sid}/events/{atlas['id']}/strike").json()
    assert st["held_question_count"] < before
    assert not any("Forwarded INV-4475" in e["text"] for e in st["events"])


def test_live_coaching_asks_at_pauses_with_pacing(client):
    sid = _run_to_end(client, mode="live")
    asked = []
    for _ in range(len(demo.SCRIPT_EVENTS) + 2):
        st = client.post(f"/api/sessions/{sid}/control", json={"action": "advance"}).json()
        q = st["live_question"]
        if q:
            asked.append(q["text"])
            client.post(f"/api/sessions/{sid}/live-answer", json={"question_id": q["id"], "answer": "Per item, net."})
    assert len(asked) >= 3
    assert any("€5,000" in t for t in asked)  # threshold question
    st = client.get(f"/api/sessions/{sid}").json()
    assert any(p["decision"] == "held" for p in st["pacing_log"])
    # Questions are only asked at pauses.
    assert all(p["decision"] in ("asked", "held", "silent") for p in st["pacing_log"])
    assert st["work_time_s"] / 60 * 0.5 >= len(asked) - 1  # ≤ ~5 per 10 minutes


def test_custom_workflow_notes_generate_questions(client):
    sid = client.post(
        "/api/sessions", json={"workflow_name": "Month-end close", "mode": "lockin", "use_demo_script": False}
    ).json()["id"]
    client.post(f"/api/sessions/{sid}/control", json={"action": "start"})
    client.post(f"/api/sessions/{sid}/notes", json={"text": "Accrued the €12,000 consulting invoice to December"})
    st = client.get(f"/api/sessions/{sid}").json()
    assert st["held_question_count"] >= 3 and st["live_question"] is None
    client.post(f"/api/sessions/{sid}/control", json={"action": "end"})
    d = client.get(f"/api/sessions/{sid}/debrief").json()
    assert "12,000" in str(d["current"]) or d["current"]["evidence"]


def test_discard(client):
    sid = _run_to_end(client)
    assert client.delete(f"/api/sessions/{sid}").status_code == 200
    assert client.get(f"/api/sessions/{sid}").status_code == 404
