"""Test config: keep the suite fast and offline-deterministic by disabling the
real Gemini call. The AI service falls back to its heuristic path when there is
no key, so tests exercise the full flow without hitting the network.
Real Gemini is tested separately/manually, not in the unit suite."""
import pytest
from app.config import settings


@pytest.fixture(autouse=True, scope="session")
def _no_live_ai():
    saved = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    yield
    settings.GEMINI_API_KEY = saved
