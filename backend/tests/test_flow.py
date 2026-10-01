"""E2E: фото -> авто-ИИ -> сообщение водителя -> вердикт -> сообщение пользователю."""
import io
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app import models

c = TestClient(app)

def _reg(phone):
    r = c.post("/api/v1/auth/register",
               json={"phone": phone, "password": "secret123", "full_name": "Flow User"})
    assert r.status_code in (201, 409)
    if r.status_code == 409:
        r = c.post("/api/v1/auth/login", json={"phone": phone, "password": "secret123"})
    return r.json()["access"]

def test_full_flow():
    import secrets
    suf = secrets.token_hex(2)
    driver_tok = _reg("+99891" + suf)
    spec_tok = _reg("+99892" + suf)
    # повышаем второго до специалиста напрямую в БД
    db = SessionLocal()
    spec = db.query(models.User).filter_by(phone="+99892" + suf).first()
    spec.role = "specialist"; db.commit(); db.close()
    # специалист перелогинивается для нового токена с ролью
    spec_tok = c.post("/api/v1/auth/login",
                      json={"phone": "+99892" + suf, "password": "secret123"}).json()["access"]
    dh = {"Authorization": f"Bearer {driver_tok}"}
    sh = {"Authorization": f"Bearer {spec_tok}"}

    inc = c.post("/api/v1/incidents", headers=dh, json={}).json()
    iid = inc["id"]
    c.post(f"/api/v1/incidents/{iid}/triage", headers=dh,
           json={"responsibility_accepted": True, "docs_valid": True,
                 "sober": True, "damage_agreed": True}).json()
    # фото (настоящий jpeg) -> авто-ИИ в ответе
    import io as _io
    from PIL import Image as _Image
    _b = _io.BytesIO(); _Image.new("RGB", (64, 48), (120, 120, 120)).save(_b, format="JPEG")
    files = {"file": ("crash.jpg", _io.BytesIO(_b.getvalue()), "image/jpeg")}
    r = c.post(f"/api/v1/incidents/{iid}/evidence-upload", headers=dh,
               data={"kind": "damage_close"}, files=files)
    assert r.status_code == 201, r.text
    assert "ai" in r.json() and "svg" in r.json()["ai"]
    # водитель пишет сотруднику
    m = c.post(f"/api/v1/incidents/{iid}/messages", headers=dh, json={"text": "Понял, жду"})
    assert m.status_code == 201
    # сотрудник видит досье с сообщениями
    det = c.get(f"/api/v1/admin/incidents/{iid}", headers=sh).json()
    assert any("Понял" in x["text"] for x in det["messages"])
    # вердикт approve -> сообщение пользователю
    det2 = det
    assert det2["review"] is None  # green-случай без ревью
    # создаём yellow-случай для ревью
    inc2 = c.post("/api/v1/incidents", headers=dh, json={}).json()
    c.post(f"/api/v1/incidents/{inc2['id']}/triage", headers=dh,
           json={"responsibility_accepted": True, "docs_valid": False,
                 "sober": True, "damage_agreed": True})
    q = c.get("/api/v1/reviews/queue", headers=sh).json()
    rid = [x["id"] for x in q if x["incident_id"] == inc2["id"]][0]
    v = c.post(f"/api/v1/reviews/{rid}", headers=sh,
               json={"verdict": "approved", "comment": ""}).json()
    assert "агенты" in v["sent_to_user"]
    msgs = c.get(f"/api/v1/incidents/{inc2['id']}/messages", headers=dh).json()
    assert any("агенты" in m["text"] for m in msgs)
