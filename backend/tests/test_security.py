"""P0 security regression tests: photo access control, upload validation, CORS,
and SECRET_KEY enforcement. Each test maps to a fix in the P0 batch."""
import io
import secrets
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.db import SessionLocal
from app import models

c = TestClient(app)


def _jpeg_bytes(w=64, h=48, color=(100, 110, 120)) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (w, h), color).save(b, format="JPEG")
    return b.getvalue()


def _reg(phone):
    r = c.post("/api/v1/auth/register",
               json={"phone": phone, "password": "secret123", "full_name": "Sec User"})
    if r.status_code == 409:
        r = c.post("/api/v1/auth/login", json={"phone": phone, "password": "secret123"})
    return r.json()["access"]


def _incident_with_photo():
    """Owner creates an incident, runs triage to 'evidence', uploads one real photo.
    Returns (owner_token, iid, evidence_id)."""
    suf = secrets.token_hex(3)
    owner = _reg("+99893" + suf)
    oh = {"Authorization": f"Bearer {owner}"}
    iid = c.post("/api/v1/incidents", headers=oh, json={}).json()["id"]
    c.post(f"/api/v1/incidents/{iid}/triage", headers=oh,
           json={"responsibility_accepted": True, "docs_valid": True,
                 "sober": True, "damage_agreed": True})
    up = c.post(f"/api/v1/incidents/{iid}/evidence-upload", headers=oh,
                data={"kind": "damage_close"},
                files={"file": ("p.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")})
    assert up.status_code == 201, up.text
    return owner, iid, up.json()["evidence_id"]


# ---- P0.1 photo access control -------------------------------------------------

def test_uploads_not_public_static():
    """The old public /uploads/<name> static mount must be gone (no 200)."""
    r = c.get("/uploads/anything.jpg")
    assert r.status_code != 200


def test_owner_can_read_own_photo():
    owner, iid, eid = _incident_with_photo()
    r = c.get(f"/api/v1/incidents/{iid}/evidence/{eid}/file",
              headers={"Authorization": f"Bearer {owner}"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/")


def test_stranger_gets_403_on_foreign_photo():
    _owner, iid, eid = _incident_with_photo()
    stranger = _reg("+99894" + secrets.token_hex(3))
    r = c.get(f"/api/v1/incidents/{iid}/evidence/{eid}/file",
              headers={"Authorization": f"Bearer {stranger}"})
    assert r.status_code == 403


def test_photo_requires_token():
    _owner, iid, eid = _incident_with_photo()
    r = c.get(f"/api/v1/incidents/{iid}/evidence/{eid}/file")
    assert r.status_code == 401


def test_specialist_can_read_any_photo():
    _owner, iid, eid = _incident_with_photo()
    phone = "+99895" + secrets.token_hex(3)
    _reg(phone)
    db = SessionLocal()
    sp = db.query(models.User).filter_by(phone=phone).first()
    sp.role = "specialist"; db.commit(); db.close()
    tok = c.post("/api/v1/auth/login",
                 json={"phone": phone, "password": "secret123"}).json()["access"]
    r = c.get(f"/api/v1/incidents/{iid}/evidence/{eid}/file?token={tok}")
    assert r.status_code == 200


# ---- P0.2 upload validation ----------------------------------------------------

def test_reject_non_image_type():
    suf = secrets.token_hex(3)
    owner = _reg("+99896" + suf)
    oh = {"Authorization": f"Bearer {owner}"}
    iid = c.post("/api/v1/incidents", headers=oh, json={}).json()["id"]
    c.post(f"/api/v1/incidents/{iid}/triage", headers=oh,
           json={"responsibility_accepted": True, "docs_valid": True,
                 "sober": True, "damage_agreed": True})
    r = c.post(f"/api/v1/incidents/{iid}/evidence-upload", headers=oh,
               data={"kind": "damage_close"},
               files={"file": ("bad.txt", io.BytesIO(b"not an image at all"), "text/plain")})
    assert r.status_code == 400


def test_reject_fake_jpeg_magic_but_corrupt():
    """JPEG magic bytes but not a real decodable image -> rejected."""
    suf = secrets.token_hex(3)
    owner = _reg("+99897" + suf)
    oh = {"Authorization": f"Bearer {owner}"}
    iid = c.post("/api/v1/incidents", headers=oh, json={}).json()["id"]
    c.post(f"/api/v1/incidents/{iid}/triage", headers=oh,
           json={"responsibility_accepted": True, "docs_valid": True,
                 "sober": True, "damage_agreed": True})
    r = c.post(f"/api/v1/incidents/{iid}/evidence-upload", headers=oh,
               data={"kind": "damage_close"},
               files={"file": ("x.jpg", io.BytesIO(b"\xff\xd8\xff" + b"junk" * 10), "image/jpeg")})
    assert r.status_code == 400


def test_reject_oversized_file():
    suf = secrets.token_hex(3)
    owner = _reg("+99898" + suf)
    oh = {"Authorization": f"Bearer {owner}"}
    iid = c.post("/api/v1/incidents", headers=oh, json={}).json()["id"]
    c.post(f"/api/v1/incidents/{iid}/triage", headers=oh,
           json={"responsibility_accepted": True, "docs_valid": True,
                 "sober": True, "damage_agreed": True})
    big = b"\xff\xd8\xff" + b"\x00" * (10 * 1024 * 1024 + 1)
    r = c.post(f"/api/v1/incidents/{iid}/evidence-upload", headers=oh,
               data={"kind": "damage_close"},
               files={"file": ("big.jpg", io.BytesIO(big), "image/jpeg")})
    assert r.status_code == 400


# ---- P0.3 CORS -----------------------------------------------------------------

def test_cors_allows_configured_origin():
    r = c.get("/health", headers={"Origin": "http://localhost:8000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:8000"


def test_cors_blocks_unknown_origin():
    r = c.get("/health", headers={"Origin": "http://evil.example.com"})
    assert r.headers.get("access-control-allow-origin") != "http://evil.example.com"


# ---- P0.3 SECRET_KEY enforcement ----------------------------------------------

@pytest.mark.parametrize("weak", ["change-me-in-prod-min-32-chars", "short", "dev-only-change-me"])
def test_secret_key_rejects_weak(weak):
    from app.config import Settings
    with pytest.raises(Exception):
        Settings(SECRET_KEY=weak, _env_file=None)
