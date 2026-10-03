"""Illuminate (onboarding) and Trial (assessment)."""


def test_illuminate_locked_until_expert_confirms(client):
    ov = client.get("/api/illuminate").json()
    assert not ov["map_ready"]
    assert all(lv["status"] == "awaiting_expert" for lv in ov["levels"])
    assert (
        client.post("/api/illuminate/precheck", json={"scenario_id": "sc-2a", "action_id": "approve-6400"}).status_code
        == 409
    )


def _master_l1(client):
    for sc, action, reason in (("sc-1a", "hold-gr", "no-gr"), ("sc-1b", "approve", "match")):
        r = client.post(
            "/api/illuminate/submit",
            json={"scenario_id": sc, "action_id": action, "reason_id": reason, "path": [{"action_id": action}]},
        )
        assert r.status_code == 200, r.text
    return r.json()


def test_tutor_catches_7200_opex_mistake_before_submission(client):
    client.post("/api/demo/fast-forward")
    lv = client.get("/api/illuminate/levels/L2").json()
    assert lv["level"]["status"] == "locked"  # prerequisite not mastered yet
    res = _master_l1(client)
    assert res["level"]["status"] == "mastered"
    lv = client.get("/api/illuminate/levels/L2").json()
    sc = next(s for s in lv["scenarios"] if s["id"] == "sc-2a")
    assert "correct_action" not in sc and "explain" not in sc  # no answer leakage before deciding
    assert sc["document"]["net"] == 7200.0 and sc["document"]["prefilled_gl"] == "6400"
    pre = client.post("/api/illuminate/precheck", json={"scenario_id": "sc-2a", "action_id": "approve-6400"}).json()
    assert pre["intervene"] is True
    assert "€5,000" in pre["message"] and pre["guardrail"]["key"] == "g-capex-5000"
    assert pre["citations"] and pre["citations"][0]["quote"]
    # Learner corrects and submits.
    r = client.post(
        "/api/illuminate/submit",
        json={
            "scenario_id": "sc-2a",
            "action_id": "recode-0720",
            "reason_id": "per-item",
            "path": [
                {"action_id": "approve-6400", "prechecked": True},
                {"action_id": "recode-0720", "prechecked": True},
            ],
        },
    ).json()
    assert r["action_correct"] and r["tutor_intervened"] and not r["guardrails_missed"]
    r = client.post(
        "/api/illuminate/submit",
        json={"scenario_id": "sc-2b", "action_id": "approve-6400", "reason_id": "per-item", "path": []},
    ).json()
    assert r["level"]["status"] == "mastered"
    s = client.get("/api/illuminate/levels/L2/summary").json()
    assert all(x["met"] for x in s["rubric"]) and "Mastered" in s["why"]


def test_practice_does_not_corrupt_progress(client):
    client.post("/api/demo/fast-forward")
    _master_l1(client)
    client.post(
        "/api/illuminate/submit",
        json={"scenario_id": "sc-1a", "action_id": "approve", "reason_id": "small", "path": [], "mode": "practice"},
    )
    ov = client.get("/api/illuminate").json()
    assert ov["levels"][0]["status"] == "mastered"
    assert client.get("/api/illuminate/levels/L1/summary").json()["practice_attempts"] == 1


def test_tutor_grounded_or_honest(client):
    r = client.post("/api/illuminate/tutor", json={"message": "what is the capex threshold?"}).json()
    assert "don't have expert-confirmed knowledge" in r["reply"]
    client.post("/api/demo/fast-forward")
    r = client.post(
        "/api/illuminate/tutor", json={"message": "is the capex line per item or per invoice?", "scenario_id": "sc-2a"}
    ).json()
    assert r["citations"] and "Mira confirmed" in r["reply"]


def test_trial_no_feedback_and_reviewer_evidence(client):
    assert client.post("/api/trial/candidates", json={"alias": "A", "consent": True}).status_code == 409
    client.post("/api/demo/fast-forward")
    assert client.post("/api/trial/candidates", json={"alias": "A", "consent": False}).status_code == 422
    token = client.post("/api/trial/candidates", json={"alias": "Candidate 7", "consent": True}).json()["token"]
    view = client.get(f"/api/trial/candidates/{token}").json()
    leak = str(view)
    assert "expected_action" not in leak and "cues" not in leak and "Mira" not in leak
    r = client.post(
        f"/api/trial/candidates/{token}/responses",
        json={
            "task_id": "T1",
            "action_id": "recode-0720",
            "rationale": "Single item over 5,000 net, so capex with asset tag",
            "path": [{"action_id": "approve-6400"}, {"action_id": "recode-0720"}],
        },
    ).json()
    assert r == {"recorded": True}
    client.post(
        f"/api/trial/candidates/{token}/responses",
        json={"task_id": "T3", "action_id": "update-pay", "rationale": "Supplier asked"},
    )
    client.post(f"/api/trial/candidates/{token}/finish")
    assert client.get("/api/trial/review").status_code == 403
    h = {"X-Reviewer-Code": "umbra-review-demo"}
    cand = client.get("/api/trial/review", headers=h).json()[0]
    det = client.get(f"/api/trial/review/{cand['id']}", headers=h).json()
    levels = {t["task"]["id"]: t["evidence_level"] for t in det["tasks"]}
    assert levels == {"T1": "demonstrated", "T2": "not_assessed", "T3": "not_demonstrated", "T4": "not_assessed"}
    assert "score" not in str(det).lower().replace("no overall score", "")
    assert det["tasks"][0]["response"]["path"]
    # Candidate can delete their own data.
    assert client.delete(f"/api/trial/candidates/{token}").status_code == 200
    assert client.get("/api/trial/review", headers=h).json() == []


def test_voice_endpoints_degrade_cleanly(client):
    assert client.get("/api/voice/config").json()["configured"] is False
    assert client.post("/api/voice/tts", json={"text": "hi"}).status_code == 503
    assert client.post("/api/voice/scribe-token").status_code == 503
    assert client.get("/api/health").json()["integrations"]["mode"] == "demo"
