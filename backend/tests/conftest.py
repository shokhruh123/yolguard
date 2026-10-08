"""Test config: keep the suite fast and offline-deterministic by disabling the
real Gemini call. The AI service falls back to its heuristic path when there is
no key, so tests exercise the full flow without hitting the network.
Real Gemini is tested separately/manually, not in the unit suite.
Rate limiting is also disabled: the whole suite shares one TestClient IP.
After the suite, test-created users and their incidents are removed so the
dev database (and the staff EXE list) does not fill with junk."""
import pytest
from app.config import settings


@pytest.fixture(autouse=True, scope="session")
def _no_live_ai():
    saved = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    yield
    settings.GEMINI_API_KEY = saved


@pytest.fixture(autouse=True, scope="session")
def _no_rate_limit():
    saved = settings.RATE_LIMIT_ENABLED
    settings.RATE_LIMIT_ENABLED = False
    yield
    settings.RATE_LIMIT_ENABLED = saved


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_data():
    from app.db import SessionLocal
    from app import models
    db = SessionLocal()
    before_users = {u.id for u in db.query(models.User).all()}
    before_incs = {i.id for i in db.query(models.Incident).all()}
    db.close()
    yield
    db = SessionLocal()
    try:
        new_uids = [u.id for u in db.query(models.User).all()
                    if u.id not in before_users]
        inc_ids = {i.id for i in db.query(models.Incident).all()
                   if i.id not in before_incs}
        for p in db.query(models.Participant).filter(
                models.Participant.user_id.in_(new_uids)).all():
            inc_ids.add(p.incident_id)
        if inc_ids:
            for m in (models.Evidence, models.Message, models.Participant,
                      models.ReviewCase, models.ClaimPackage, models.AIAnalysis,
                      models.Diagram):
                db.query(m).filter(m.incident_id.in_(inc_ids)).delete(
                    synchronize_session=False)
            db.query(models.Incident).filter(
                models.Incident.id.in_(inc_ids)).delete(synchronize_session=False)
        if new_uids:
            db.query(models.Vehicle).filter(
                models.Vehicle.owner_id.in_(new_uids)).delete(synchronize_session=False)
            db.query(models.PushSubscription).filter(
                models.PushSubscription.user_id.in_(new_uids)).delete(
                    synchronize_session=False)
            db.query(models.User).filter(
                models.User.id.in_(new_uids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
