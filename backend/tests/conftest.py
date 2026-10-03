import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Hermetic: no external credentials, fresh database per test.
    for var in ("ELEVENLABS_API_KEY", "LLM_PROVIDER", "LLM_API_KEY", "VISION_PROVIDER", "VISION_API_KEY"):
        monkeypatch.setenv(var, "")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from app import db
    from app.config import get_settings

    get_settings.cache_clear()
    db.init_db(reset=True)
    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
