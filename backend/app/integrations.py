"""Optional external services. Each call returns None on any failure so callers fall back to the demo path.

Keys never leave the server. Nothing here is required for the demo.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from .config import get_settings

log = logging.getLogger("umbra.integrations")

ELEVEN_BASE = "https://api.elevenlabs.io"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def status() -> dict[str, Any]:
    s = get_settings()
    return {
        "mode": "live" if (s.elevenlabs_enabled or s.llm_enabled or s.vision_enabled) else "demo",
        "elevenlabs": {
            "configured": s.elevenlabs_enabled,
            "tts": bool(s.elevenlabs_enabled and s.elevenlabs_voice_id),
            "stt": s.elevenlabs_enabled,
            "scribe_realtime": s.elevenlabs_enabled,
            "interviewer_agent": bool(s.elevenlabs_enabled and s.elevenlabs_agent_id_interviewer),
            "tutor_agent": bool(s.elevenlabs_enabled and s.elevenlabs_agent_id_tutor),
        },
        "llm": {"configured": s.llm_enabled, "provider": s.llm_provider or None},
        "vision": {"configured": s.vision_enabled, "provider": s.vision_provider or None},
    }


# ---------------------------------------------------------------------------------------------------------------
# LLM / vision (Anthropic Messages API or an OpenAI-compatible Chat Completions API)
# ---------------------------------------------------------------------------------------------------------------


def _chat(
    provider: str, key: str, model: str, system: str, content: list[dict[str, Any]] | str, max_tokens: int = 800
) -> str | None:
    try:
        if provider == "anthropic":
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={
                    "model": model or "claude-sonnet-5-5",
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": content}],
                },
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
        if provider == "openai":
            if isinstance(content, list):
                oa_content: Any = [
                    {"type": "text", "text": c["text"]}
                    if c["type"] == "text"
                    else {
                        "type": "image_url",
                        "image_url": {"url": f"data:{c['source']['media_type']};base64,{c['source']['data']}"},
                    }
                    for c in content
                ]
            else:
                oa_content = content
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"authorization": f"Bearer {key}"},
                json={
                    "model": model or "gpt-4o-mini",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": oa_content}],
                },
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 — any failure means "use the deterministic fallback"
        log.warning("LLM/vision call failed (%s): %s", provider, exc)
    return None


def llm_text(system: str, prompt: str, max_tokens: int = 800) -> str | None:
    s = get_settings()
    if not s.llm_enabled:
        return None
    return _chat(s.llm_provider, s.llm_api_key, s.llm_model, system, prompt, max_tokens)


def llm_json(system: str, prompt: str, max_tokens: int = 1200) -> Any | None:
    text = llm_text(system + "\nRespond with JSON only, no prose.", prompt, max_tokens)
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("\n") + 1 :] if "\n" in text else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start == -1:
            start, end = text.find("{"), text.rfind("}")
        try:
            return json.loads(text[start : end + 1]) if start != -1 else None
        except json.JSONDecodeError:
            return None


def describe_frame(jpeg_b64: str) -> str | None:
    """Ask a vision model what changed on screen. Only the text description is stored — never the frame."""
    s = get_settings()
    if not s.vision_enabled:
        return None
    content: list[dict[str, Any]] = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": jpeg_b64}},
        {
            "type": "text",
            "text": "In one sentence, describe the work action visible on this screen (application, "
            "record and the action taken). Do not transcribe personal data.",
        },
    ]
    return _chat(
        s.vision_provider,
        s.vision_api_key,
        s.vision_model,
        "You observe an expert's screen to learn their workflow. Be brief and factual.",
        content,
        120,
    )


# ---------------------------------------------------------------------------------------------------------------
# ElevenLabs
# ---------------------------------------------------------------------------------------------------------------


def _xi_headers() -> dict[str, str]:
    return {"xi-api-key": get_settings().elevenlabs_api_key}


def tts(text: str) -> bytes | None:
    s = get_settings()
    if not (s.elevenlabs_enabled and s.elevenlabs_voice_id):
        return None
    try:
        r = httpx.post(
            f"{ELEVEN_BASE}/v1/text-to-speech/{s.elevenlabs_voice_id}",
            headers={**_xi_headers(), "accept": "audio/mpeg"},
            json={"text": text[:2000], "model_id": s.elevenlabs_tts_model},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.content
    except Exception as exc:  # noqa: BLE001
        log.warning("ElevenLabs TTS failed: %s", exc)
        return None


def stt(audio: bytes, filename: str, content_type: str) -> str | None:
    s = get_settings()
    if not s.elevenlabs_enabled:
        return None
    try:
        r = httpx.post(
            f"{ELEVEN_BASE}/v1/speech-to-text",
            headers=_xi_headers(),
            data={"model_id": s.elevenlabs_stt_model},
            files={"file": (filename, audio, content_type)},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("text")
    except Exception as exc:  # noqa: BLE001
        log.warning("ElevenLabs STT failed: %s", exc)
        return None


def scribe_token() -> str | None:
    """Single-use token so the browser can stream to Scribe v2 Realtime without seeing the API key."""
    s = get_settings()
    if not s.elevenlabs_enabled:
        return None
    try:
        r = httpx.post(f"{ELEVEN_BASE}/v1/single-use-token/realtime_scribe", headers=_xi_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("token")
    except Exception as exc:  # noqa: BLE001
        log.warning("ElevenLabs Scribe token failed: %s", exc)
        return None


def agent_signed_url(role: str) -> str | None:
    s = get_settings()
    agent_id = s.elevenlabs_agent_id_interviewer if role == "interviewer" else s.elevenlabs_agent_id_tutor
    if not (s.elevenlabs_enabled and agent_id):
        return None
    try:
        r = httpx.get(
            f"{ELEVEN_BASE}/v1/convai/conversation/get-signed-url",
            params={"agent_id": agent_id},
            headers=_xi_headers(),
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("signed_url")
    except Exception as exc:  # noqa: BLE001
        log.warning("ElevenLabs signed URL failed: %s", exc)
        return None
