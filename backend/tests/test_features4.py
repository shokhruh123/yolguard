"""Iteration-4 features: media upload, AI plates/severity, insurer role,
push subscriptions, rate limiting."""
import io
import time
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services import ai as ai_svc

c = TestClient(app)
JPEG = (b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64)


def _reg(phone, role=None):
    r = c.post("/api/v1/auth/register",
               json={"phone": phone, "password": "secret12", "full_name": "Test User"})
    if r.status_code == 409:
        r = c.post("/api/v1/auth/login", json={"phone": phone, "password": "secret12"})
    j = r.json()
    if role and j["user"]["role"] != role:
        from app.db import SessionLocal
        from app import models
        db = SessionLocal()
        u = db.query(models.User).filter_by(phone=phone).first()
        u.role = role; db.commit(); db.close()
        r = c.post("/api/v1/auth/login", json={"phone": phone, "password": "secret12"})
        j = r.json()
    return j["access"], j["user"]


def _inc(token):
    return c.post("/api/v1/incidents", json={},
                  headers={"Authorization": f"Bearer {token}"}).json()["id"]


def _real_jpeg():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 30, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def test_video_upload_ok_and_bad_rejected():
    token, _ = _reg(f"+99890201{int(time.time()) % 100000:05d}")
    iid = _inc(token)
    h = {"Authorization": f"Bearer {token}"}
    mp4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + b"\x00" * 100
    r = c.post(f"/api/v1/incidents/{iid}/evidence-upload",
               files={"file": ("clip.mp4", mp4, "video/mp4")},
               data={"kind": "video_scene"}, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["saved"] is True
    # photo kind with video bytes -> 400
    r2 = c.post(f"/api/v1/incidents/{iid}/evidence-upload",
                files={"file": ("clip.mp4", mp4, "video/mp4")},
                data={"kind": "damage_close"}, headers=h)
    assert r2.status_code == 400, r2.text
    # unknown media kind value rejected by allow-list
    r3 = c.post(f"/api/v1/incidents/{iid}/evidence-upload",
                files={"file": ("x.mp3", b"ID3" + b"\x00" * 100, "audio/mpeg")},
                data={"kind": "hacker_kind"}, headers=h)
    assert r3.status_code == 400, r3.text


def test_voice_note_upload_ok():
    token, _ = _reg(f"+99890202{int(time.time()) % 100000:05d}")
    iid = _inc(token)
    mp3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 200
    r = c.post(f"/api/v1/incidents/{iid}/evidence-upload",
               files={"file": ("note.mp3", mp3, "audio/mpeg")},
               data={"kind": "voice_note"},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text


def test_heuristic_has_plates_and_severity():
    res = ai_svc.heuristic_reason({}, [])
    assert res["plates"] == {"a": "", "b": ""}
    assert res["damage_severity"] == "unknown"


def test_heuristic_svg_varies_by_impact():
    from app.services.ai import heuristic_svg
    a = heuristic_svg(impact="Передний бампер")
    b = heuristic_svg(impact="Задний бампер")
    c = heuristic_svg()
    assert a.startswith("<svg") and b.startswith("<svg")
    assert a != b, "схема должна отличаться для разного impact_part"
    assert "Передний бампер" in a
    assert c != a


def test_road_scene_elements():
    from app.services.ai import heuristic_svg
    svg = heuristic_svg(label_a="A", label_b="B", impact="Левый бок")
    for needle in ("<polygon", "вид сверху", ">A<", ">B<", "удар", "marker"):
        assert needle in svg, needle
    assert "<script" not in svg


def test_insurer_read_only():
    drv, _ = _reg(f"+99890203{int(time.time()) % 100000:05d}")
    iid = _inc(drv)
    h_drv = {"Authorization": f"Bearer {drv}"}
    # no claim yet -> 404 for driver too
    assert c.get(f"/api/v1/incidents/{iid}/claim-package", headers=h_drv).status_code == 404
    # insurer blocked from specialist-only queue, allowed on insurer list
    ins, _ = _reg(f"+99890204{int(time.time()) % 100000:05d}", role="insurer")
    h_ins = {"Authorization": f"Bearer {ins}"}
    assert c.get("/api/v1/reviews/queue", headers=h_ins).status_code == 403
    r = c.get("/api/v1/insurer/incidents", headers=h_ins)
    assert r.status_code == 200 and isinstance(r.json(), list), r.text
    # insurer cannot write messages (not a participant)
    r2 = c.post(f"/api/v1/incidents/{iid}/messages", json={"text": "hi"}, headers=h_ins)
    assert r2.status_code == 403, r2.text


def test_push_subscribe_cycle_and_vapid():
    token, _ = _reg(f"+99890205{int(time.time()) % 100000:05d}")
    h = {"Authorization": f"Bearer {token}"}
    assert "publicKey" in c.get("/api/v1/push/vapid-key").json()
    sub = {"endpoint": f"https://example.com/push/{int(time.time())}",
           "keys": {"p256dh": "B" * 20, "auth": "A" * 20}}
    assert c.post("/api/v1/push/subscribe", json=sub, headers=h).status_code == 201
    assert c.post("/api/v1/push/unsubscribe", json=sub, headers=h).status_code == 200


def test_rate_limit_kicks_in_when_enabled():
    saved = settings.RATE_LIMIT_ENABLED
    settings.RATE_LIMIT_ENABLED = True
    try:
        codes = set()
        for _ in range(25):
            r = c.post("/api/v1/auth/login",
                       json={"phone": "+998900000000", "password": "wrongwrong"})
            codes.add(r.status_code)
        assert 429 in codes, codes
    finally:
        settings.RATE_LIMIT_ENABLED = saved


def test_upload_auth_still_required():
    r = c.post("/api/v1/incidents/1/evidence-upload",
               files={"file": ("p.jpg", JPEG, "image/jpeg")},
               data={"kind": "damage_close"})
    assert r.status_code == 401, r.text
