"""Runtime configuration. Every external integration is optional.

When a key is missing, Umbra runs in a deterministic, clearly labelled demo mode.
Secrets are only ever read here, on the server, and never returned to the client.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id_interviewer: str = ""
    elevenlabs_agent_id_tutor: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_tts_model: str = "eleven_flash_v2_5"
    elevenlabs_stt_model: str = "scribe_v2"

    # LLM (debrief phrasing, teach-back paraphrase, tutor answers)
    llm_provider: str = ""  # "anthropic" | "openai"
    llm_api_key: str = ""
    llm_model: str = ""

    # Vision (occasional screen-frame understanding)
    vision_provider: str = ""  # "anthropic" | "openai"
    vision_api_key: str = ""
    vision_model: str = ""

    database_url: str = "sqlite:///./umbra.db"

    # Demo access code for the Trial reviewer console (not a secret — change it in production).
    reviewer_access_code: str = "umbra-review-demo"
    candidate_retention_days: int = 30

    @property
    def database_path(self) -> str:
        url = self.database_url
        path = url[len("sqlite:///") :] if url.startswith("sqlite:///") else url
        if path == ":memory:":
            return path
        p = Path(path)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        return str(p)

    @property
    def elevenlabs_enabled(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_provider and self.llm_api_key)

    @property
    def vision_enabled(self) -> bool:
        return bool(self.vision_provider and self.vision_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
