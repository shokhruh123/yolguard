"""Modular monolith. Versioned API /api/v1. Frontend served as static demo."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .db import Base, engine, ensure_schema
from .routers import auth, incidents, misc, admin

os.makedirs("uploads", exist_ok=True)
Base.metadata.create_all(bind=engine)
ensure_schema()
app = FastAPI(title="Yo'l Guard API", version="0.3.0")

# Explicit CORS allow-list from .env — never "*". allow_credentials needs exact origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(misc.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

# NOTE: /uploads is intentionally NOT mounted as public static files.
# Evidence photos are served only through the auth-gated endpoint
# GET /api/v1/incidents/{iid}/evidence/{eid}/file (participants + specialist/admin).

@app.get("/health")
def health():
    return {"ok": True, "service": "yolguard"}

try:
    app.mount("/app", StaticFiles(directory="../frontend", html=True), name="frontend")
except Exception:
    pass
