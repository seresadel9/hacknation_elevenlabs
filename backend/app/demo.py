"""Demo helpers: reset and "fast-forward" (runs the real pipeline end-to-end with Mira's seeded answers)."""

from __future__ import annotations

from typing import Any

from . import capture, mapbuilder
from . import demo_script as demo
from .db import tx, wipe_all


def reset() -> None:
    wipe_all()


def fast_forward() -> dict[str, Any]:
    """Capture → debrief → teach-back → commit, using exactly the same code paths a person would."""
    st = capture.create_session(demo.DEMO_WORKFLOW_NAME, "lockin", use_demo_script=True, screen_share=False)
    sid = st["id"]
    capture.control(sid, "start")
    with tx() as c:
        c.execute("UPDATE sessions SET offset_s=? WHERE id=?", (demo.SCRIPT_END_T + 1, sid))
    capture.state(sid)
    capture.control(sid, "end")
    while True:
        d = capture.debrief(sid)
        q = d["current"]
        if q is None:
            break
        capture.answer_debrief(sid, q["id"], q["sample_answer"], skip=False)
    capture.finish_debrief(sid)
    tb = mapbuilder.teachback(sid)
    for item in tb["items"]:
        if item["confirmable"]:
            mapbuilder.update_item(item["id"], "confirmed", None)
    result = mapbuilder.commit(sid)
    return {"session_id": sid, "lit": result["lit"], "counts": result["graph"]["counts"]}
