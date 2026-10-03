"""Umbra API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, File, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import capture, demo, illuminate, integrations, mapbuilder, trial
from .db import init_db

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):  # type: ignore[no-untyped-def]
    init_db()
    yield


app = FastAPI(title="Umbra API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------------------------------- request models
class NewSession(BaseModel):
    workflow_name: str = Field(default="", max_length=120)
    mode: Literal["lockin", "live"] = "lockin"
    use_demo_script: bool = True
    screen_share: bool = False


class Control(BaseModel):
    action: Literal["start", "pause", "resume", "end", "advance"]


class OffRecord(BaseModel):
    on: bool


class Note(BaseModel):
    text: str = Field(max_length=1000)
    kind: Literal["note", "transcript"] = "note"


class ScreenSignal(BaseModel):
    kind: Literal["change", "idle"]
    score: float | None = None
    frame_jpeg_b64: str | None = Field(default=None, max_length=600_000)


class Answer(BaseModel):
    question_id: str
    answer: str | None = Field(default=None, max_length=4000)
    skip: bool = False
    defer: bool = False


class ItemUpdate(BaseModel):
    status: Literal["confirmed", "edited", "rejected", "pending"]
    text: str | None = Field(default=None, max_length=4000)


class Precheck(BaseModel):
    scenario_id: str
    action_id: str


class Submit(BaseModel):
    scenario_id: str
    action_id: str
    reason_id: str | None = None
    path: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    mode: Literal["learn", "practice"] = "learn"


class TutorMsg(BaseModel):
    message: str = Field(max_length=1000)
    scenario_id: str | None = None
    decided: bool = False


class StartTrial(BaseModel):
    alias: str = Field(default="", max_length=60)
    consent: bool


class TrialResponse(BaseModel):
    task_id: str
    action_id: str
    rationale: str = Field(default="", max_length=2000)
    path: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    time_spent_s: float | None = None


class TTSReq(BaseModel):
    text: str = Field(max_length=2000)


# ----------------------------------------------------------------------------------------------- system
@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "integrations": integrations.status()}


@app.post("/api/demo/reset")
def demo_reset() -> dict[str, Any]:
    demo.reset()
    return {"ok": True}


@app.post("/api/demo/fast-forward")
def demo_fast_forward() -> dict[str, Any]:
    return demo.fast_forward()


# ----------------------------------------------------------------------------------------------- capture
@app.post("/api/sessions")
def create_session(body: NewSession) -> dict[str, Any]:
    return capture.create_session(body.workflow_name, body.mode, body.use_demo_script, body.screen_share)


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    return capture.list_sessions()


@app.get("/api/sessions/{sid}")
def get_session(sid: str) -> dict[str, Any]:
    return capture.state(sid)


@app.post("/api/sessions/{sid}/control")
def control(sid: str, body: Control) -> dict[str, Any]:
    return capture.control(sid, body.action)


@app.delete("/api/sessions/{sid}")
def discard(sid: str) -> dict[str, Any]:
    capture.discard(sid)
    return {"discarded": True}


@app.post("/api/sessions/{sid}/off-record")
def off_record(sid: str, body: OffRecord) -> dict[str, Any]:
    return capture.set_off_record(sid, body.on)


@app.post("/api/sessions/{sid}/events/{eid}/strike")
def strike(sid: str, eid: str) -> dict[str, Any]:
    return capture.strike_event(sid, eid)


@app.post("/api/sessions/{sid}/notes")
def note(sid: str, body: Note) -> dict[str, Any]:
    return capture.add_note(sid, body.text, body.kind)


@app.post("/api/sessions/{sid}/screen")
def screen(sid: str, body: ScreenSignal) -> dict[str, Any]:
    description = integrations.describe_frame(body.frame_jpeg_b64) if body.frame_jpeg_b64 else None
    # The frame itself is discarded here — only the text description (if any) is stored.
    return capture.screen_signal(sid, body.kind, body.score, description)


@app.post("/api/sessions/{sid}/live-answer")
def live_answer(sid: str, body: Answer) -> dict[str, Any]:
    return capture.answer_live(sid, body.question_id, body.answer, body.defer)


@app.get("/api/sessions/{sid}/debrief")
def get_debrief(sid: str) -> dict[str, Any]:
    return capture.debrief(sid)


@app.post("/api/sessions/{sid}/debrief/answer")
def debrief_answer(sid: str, body: Answer) -> dict[str, Any]:
    return capture.answer_debrief(sid, body.question_id, body.answer, body.skip)


@app.post("/api/sessions/{sid}/debrief/finish")
def debrief_finish(sid: str) -> dict[str, Any]:
    return capture.finish_debrief(sid)


@app.get("/api/sessions/{sid}/teachback")
def get_teachback(sid: str) -> dict[str, Any]:
    return mapbuilder.teachback(sid)


@app.patch("/api/teachback/{item_id}")
def patch_item(item_id: str, body: ItemUpdate) -> dict[str, Any]:
    return mapbuilder.update_item(item_id, body.status, body.text)


@app.post("/api/sessions/{sid}/commit")
def commit(sid: str) -> dict[str, Any]:
    return mapbuilder.commit(sid)


# ----------------------------------------------------------------------------------------------- work map
@app.get("/api/graph")
def get_graph() -> dict[str, Any]:
    return mapbuilder.graph()


@app.get("/api/graph/nodes/{key}")
def get_node(key: str) -> dict[str, Any]:
    return mapbuilder.node_detail(key)


# ----------------------------------------------------------------------------------------------- illuminate
@app.get("/api/illuminate")
def il_overview() -> dict[str, Any]:
    return illuminate.overview()


@app.get("/api/illuminate/levels/{level_id}")
def il_level(level_id: str) -> dict[str, Any]:
    return illuminate.level_detail(level_id)


@app.get("/api/illuminate/levels/{level_id}/summary")
def il_summary(level_id: str) -> dict[str, Any]:
    return illuminate.summary(level_id)


@app.post("/api/illuminate/precheck")
def il_precheck(body: Precheck) -> dict[str, Any]:
    return illuminate.precheck(body.scenario_id, body.action_id)


@app.post("/api/illuminate/submit")
def il_submit(body: Submit) -> dict[str, Any]:
    return illuminate.submit(body.scenario_id, body.action_id, body.reason_id, body.path, body.mode)


@app.post("/api/illuminate/tutor")
def il_tutor(body: TutorMsg) -> dict[str, Any]:
    return illuminate.tutor(body.message, body.scenario_id, body.decided)


@app.post("/api/illuminate/reset")
def il_reset() -> dict[str, Any]:
    illuminate.reset()
    return {"ok": True}


# ----------------------------------------------------------------------------------------------- trial
@app.get("/api/trial/brief")
def tr_brief() -> dict[str, Any]:
    return trial.brief()


@app.post("/api/trial/candidates")
def tr_start(body: StartTrial) -> dict[str, Any]:
    return trial.start(body.alias, body.consent)


@app.get("/api/trial/candidates/{token}")
def tr_view(token: str) -> dict[str, Any]:
    return trial.candidate_view(token)


@app.post("/api/trial/candidates/{token}/responses")
def tr_respond(token: str, body: TrialResponse) -> dict[str, Any]:
    return trial.respond(token, body.task_id, body.action_id, body.rationale, body.path, body.time_spent_s)


@app.post("/api/trial/candidates/{token}/finish")
def tr_finish(token: str) -> dict[str, Any]:
    return trial.finish(token)


@app.delete("/api/trial/candidates/{token}")
def tr_delete(token: str) -> dict[str, Any]:
    trial.delete_own(token)
    return {"deleted": True}


@app.get("/api/trial/review")
def tr_review(x_reviewer_code: str | None = Header(default=None)) -> list[dict[str, Any]]:
    trial.require_reviewer(x_reviewer_code)
    return trial.review_list()


@app.get("/api/trial/review/{cid}")
def tr_review_detail(cid: str, x_reviewer_code: str | None = Header(default=None)) -> dict[str, Any]:
    trial.require_reviewer(x_reviewer_code)
    return trial.review_detail(cid)


@app.delete("/api/trial/review/{cid}")
def tr_review_delete(cid: str, x_reviewer_code: str | None = Header(default=None)) -> dict[str, Any]:
    trial.require_reviewer(x_reviewer_code)
    trial.review_delete(cid)
    return {"deleted": True}


# ----------------------------------------------------------------------------------------------- voice
@app.get("/api/voice/config")
def voice_config() -> dict[str, Any]:
    return integrations.status()["elevenlabs"]


@app.post("/api/voice/tts")
def voice_tts(body: TTSReq) -> Response:
    audio = integrations.tts(body.text)
    if audio is None:
        raise HTTPException(503, "Voice is not configured (ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID) or unavailable.")
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/voice/stt")
async def voice_stt(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
    data = await file.read()
    if len(data) > 15_000_000:
        raise HTTPException(413, "Recording too long.")
    text = integrations.stt(data, file.filename or "answer.webm", file.content_type or "audio/webm")
    if text is None:
        raise HTTPException(503, "Speech-to-text is not configured (ELEVENLABS_API_KEY) or unavailable.")
    return {"text": text}


@app.post("/api/voice/scribe-token")
def voice_scribe_token() -> dict[str, Any]:
    token = integrations.scribe_token()
    if token is None:
        raise HTTPException(503, "Scribe v2 Realtime is not configured or unavailable.")
    return {"token": token}


@app.get("/api/voice/agent-url")
def voice_agent_url(role: Literal["interviewer", "tutor"]) -> dict[str, Any]:
    url = integrations.agent_signed_url(role)
    if url is None:
        raise HTTPException(503, f"The ElevenAgents {role} agent is not configured or unavailable.")
    return {"signed_url": url}
