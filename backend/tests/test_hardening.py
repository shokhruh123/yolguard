"""Hardening regression tests: token types, kind allow-list, XSS, claim rule,
verdict guards, admin stats/pagination, SVG sanitizer."""
import time
from fastapi.testclient import TestClient
from jose import jwt
from app.main import app
from app.config import settings
from app import security
from app.services.ai import _sanitize_svg

c = TestClient(app)


def _reg(phone):
    r = c.post("/api/v1/auth/register",
               json={"phone": phone, "password": "secret12", "full_name": "Test User"})
    assert r.status_code in (200, 201, 409), r.text
    if r.status_code == 409:
        r = c.post("/api/v1/auth/login", json={"phone": phone, "password": "secret12"})
    j = r.json()
    return j["access"], j["refresh"], j["user"]


def _inc(token):
    r = c.post("/api/v1/incidents", json={},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    return r.json()["id"], r.json()["code"]


def test_access_token_rejected_as_refresh():
    access, _, _ = _reg(f"+99890101{int(time.time()) % 100000:05d}")
    r = c.post("/api/v1/auth/refresh", json={"token": access})
    assert r.status_code == 401, r.text


def test_legacy_untyped_token_still_refreshes():
    # tokens issued before 'typ' existed must keep working (backwards compat)
    _, refresh, user = _reg(f"+99890102{int(time.time()) % 100000:05d}")
    legacy = jwt.encode({"sub": str(user["id"])}, settings.SECRET_KEY, algorithm="HS256")
    r = c.post("/api/v1/auth/refresh", json={"token": legacy})
    assert r.status_code == 200 and "access" in r.json(), r.text
    # new-style refresh via JSON body also works
    r2 = c.post("/api/v1/auth/refresh", json={"token": refresh})
    assert r2.status_code == 200, r2.text


def test_bad_evidence_kind_rejected():
    token, _, _ = _reg(f"+99890103{int(time.time()) % 100000:05d}")
    iid, _ = _inc(token)
    r = c.post(f"/api/v1/incidents/{iid}/evidence",
               json={"kind": "../../etc", "file_path": "x.jpg"},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400, r.text


def test_diagram_labels_escaped():
    token, _, _ = _reg(f"+99890104{int(time.time()) % 100000:05d}")
    iid, _ = _inc(token)
    evil = "<script>"  # 8 chars: passes max_length=12, must still be escaped
    r = c.post(f"/api/v1/incidents/{iid}/diagram",
               json={"label_a": evil, "label_b": "B"},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert "<script>" not in r.json()["svg"]
    assert "&lt;script&gt;" in r.json()["svg"]


def test_claim_needs_creator_confirm():
    token, _, _ = _reg(f"+99890105{int(time.time()) % 100000:05d}")
    iid, _ = _inc(token)
    r = c.post("/api/v1/auth/login",
               json={"phone": "+998900000002", "password": "spec1234"})
    if r.status_code != 200:  # seed user may not exist in this db
        return
    spec = r.json()["access"]
    # без подтверждения создателя — 400
    r0 = c.post(f"/api/v1/incidents/{iid}/claim-package",
                headers={"Authorization": f"Bearer {spec}"})
    assert r0.status_code == 400, r0.text
    # создатель подтвердил — пакета собирается и без второго водителя
    c.post(f"/api/v1/incidents/{iid}/confirm",
           headers={"Authorization": f"Bearer {token}"})
    r2 = c.post(f"/api/v1/incidents/{iid}/claim-package",
                headers={"Authorization": f"Bearer {spec}"})
    assert r2.status_code == 201, r2.text
    assert "package_hash" in r2.json()


def test_verdict_guards():
    token, _, _ = _reg(f"+99890106{int(time.time()) % 100000:05d}")
    iid, _ = _inc(token)
    # force yellow triage -> creates review case
    c.post(f"/api/v1/incidents/{iid}/triage",
           json={"damage_agreed": False, "responsibility_accepted": True,
                 "sober": True, "docs_valid": False},
           headers={"Authorization": f"Bearer {token}"})
    r = c.post("/api/v1/auth/login",
               json={"phone": "+998900000002", "password": "spec1234"})
    if r.status_code != 200:
        return
    spec = r.json()["access"]
    q = c.get("/api/v1/reviews/queue",
              headers={"Authorization": f"Bearer {spec}"}).json()
    rid = [x["id"] for x in q if x["incident_id"] == iid][0]
    # reject without comment -> 400
    r1 = c.post(f"/api/v1/reviews/{rid}", json={"verdict": "rejected"},
                headers={"Authorization": f"Bearer {spec}"})
    assert r1.status_code == 400, r1.text
    # approve ok, second verdict -> 409
    r2 = c.post(f"/api/v1/reviews/{rid}", json={"verdict": "approved"},
                headers={"Authorization": f"Bearer {spec}"})
    assert r2.status_code == 200, r2.text
    r3 = c.post(f"/api/v1/reviews/{rid}", json={"verdict": "approved"},
                headers={"Authorization": f"Bearer {spec}"})
    assert r3.status_code == 409, r3.text


def test_admin_stats_and_pagination():
    token, _, _ = _reg(f"+99890107{int(time.time()) % 100000:05d}")
    r = c.post("/api/v1/auth/login",
               json={"phone": "+998900000002", "password": "spec1234"})
    if r.status_code != 200:
        return
    spec = r.json()["access"]
    h = {"Authorization": f"Bearer {spec}"}
    s = c.get("/api/v1/admin/stats", headers=h)
    assert s.status_code == 200, s.text
    j = s.json()
    assert {"incidents_total", "by_status", "reviews_pending",
            "users_total", "mongo_enabled", "recent"} <= set(j)
    lst = c.get("/api/v1/admin/incidents?limit=1", headers=h).json()
    assert "total" in lst and "items" in lst and len(lst["items"]) <= 1


def test_ai_history_without_mongo():
    token, _, _ = _reg(f"+99890108{int(time.time()) % 100000:05d}")
    iid, _ = _inc(token)
    r = c.get(f"/api/v1/incidents/{iid}/ai-history",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["items"] == []  # no server in CI -> graceful empty


def test_sanitize_svg():
    dirty = '<svg><rect onclick="alert(1)" href="javascript:evil()"/><script>x</script><text>t</text></svg>'
    clean = _sanitize_svg(dirty)
    assert "<script" not in clean and "onclick" not in clean and "javascript:" not in clean
    assert "<text>t</text>" in clean
    assert _sanitize_svg("garbage").startswith("<svg")


def test_gemini_model_setting_exists():
    assert hasattr(settings, "GEMINI_MODEL")
    assert hasattr(settings, "MONGODB_URI")
    assert hasattr(settings, "UPLOAD_DIR")
    assert security.decode_token(security.refresh_token(1), expect="refresh") == 1
