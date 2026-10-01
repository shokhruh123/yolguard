"""API integration test. Requires: pip install -r requirements.txt"""
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

def test_health():
    assert c.get("/health").json()["ok"] is True

def test_register_login_flow():
    import secrets
    phone = "+99899" + secrets.token_hex(3)[:6]
    r = c.post("/api/v1/auth/register", json={"phone": phone, "password": "secret123", "full_name": "Test User"})
    assert r.status_code == 201
    tok = r.json()["access"]
    r2 = c.post("/api/v1/incidents", headers={"Authorization": f"Bearer {tok}"}, json={})
    assert r2.status_code == 201
