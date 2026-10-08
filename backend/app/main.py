"""Modular monolith. Versioned API /api/v1. Frontend served as static demo."""
import logging
import os
import time
from collections import defaultdict, deque
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .db import Base, engine, ensure_schema
from .routers import auth, incidents, misc, admin, push

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("yolguard")

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
Base.metadata.create_all(bind=engine)
ensure_schema()
app = FastAPI(title="Yo'l Guard API", version="0.4.0")
log.info("upload_dir=%s mongo=%s", settings.UPLOAD_DIR,
         "enabled" if (settings.MONGODB_URI or "").strip() else "disabled")

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
app.include_router(push.router, prefix="/api/v1")

# In-memory sliding-window rate limit (защита /auth и /join от брутфорса;
# для prod всё равно ставить reverse proxy с лимитами).
_RATE_LIMITS = [("/api/v1/auth/", 20, 60), ("/join", 10, 60),
                ("/evidence-upload", 30, 60)]
_hits: dict[str, deque] = defaultdict(deque)

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    path = request.url.path
    key = None
    if settings.RATE_LIMIT_ENABLED:
        for prefix, limit, window in _RATE_LIMITS:
            if prefix in path:
                ip = (request.client.host if request.client else "?")
                key = (ip, prefix, limit, window)
                break
    if key:
        _, _, limit, window = key
        now = time.monotonic()
        q = _hits[str(key)]
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= limit:
            return JSONResponse({"detail": "Too many requests, slow down"},
                                status_code=429)
        q.append(now)
    return await call_next(request)

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
