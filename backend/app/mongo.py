"""MongoDB document store — used ALONGSIDE SQL, never instead of it.

SQL remains the source of truth for: users, roles, vehicles, incidents,
participants, statuses, evidence file metadata, claim packages, review cases.

MongoDB holds document-oriented / append-only data that does not need
relations or transactions:
  - ai_analyses      — full AI/CV results per incident (one doc per run,
                       SQL keeps only the latest summary);
  - processing_events — audit/event log (upload -> AI -> review -> claim);
  - evidence_meta    — CV metadata per file (quality, detected objects...).

When MONGODB_URI is empty or the server/driver is unavailable, everything
here degrades gracefully to no-op / empty results — SQL flow keeps working.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .config import settings

log = logging.getLogger("yolguard.mongo")

_client = None
_db = None
_tried = False


def _connect():
    global _client, _db, _tried
    if _tried:
        return _db
    _tried = True
    uri = (settings.MONGODB_URI or "").strip()
    if not uri:
        return None
    try:
        import pymongo
    except ImportError:
        log.warning("MONGODB_URI set but pymongo is not installed — Mongo disabled")
        return None
    try:
        _client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")
        _db = _client[settings.MONGODB_DB or "yolguard"]
        # indexes (best-effort, idempotent)
        _db.ai_analyses.create_index([("incident_id", 1), ("created_at", -1)])
        _db.processing_events.create_index([("incident_id", 1), ("created_at", -1)])
        _db.processing_events.create_index("kind")
        _db.evidence_meta.create_index("evidence_id", unique=True)
        log.info("MongoDB connected: db=%s", _db.name)
    except Exception as e:
        log.warning("MongoDB unavailable (%s) — continuing with SQL only", e)
        _client, _db = None, None
    return _db


def mongo_enabled() -> bool:
    """True only when a live MongoDB connection exists."""
    return _connect() is not None


def reset_for_tests() -> None:
    """Drop cached client (tests only)."""
    global _client, _db, _tried
    _client, _db, _tried = None, None, False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def store_ai_analysis(incident_id: int, result: dict, meta: dict | None = None) -> Optional[Any]:
    """Persist one AI run document. Returns inserted id or None when disabled."""
    db = _connect()
    if db is None:
        return None
    doc = {
        "incident_id": incident_id,
        "source": result.get("source", ""),
        "description": result.get("description", ""),
        "casualties_note": result.get("casualties_note", ""),
        "actions": list(result.get("actions", []) or []),
        # SVG can be large — keep a bounded copy, full SVG stays in SQL summary.
        "svg": (result.get("svg", "") or "")[:20000],
        "meta": dict(meta or {}),
        "created_at": _now(),
    }
    try:
        return db.ai_analyses.insert_one(doc).inserted_id
    except Exception as e:
        log.warning("mongo store_ai_analysis failed: %s", e)
        return None


def log_event(incident_id: int, kind: str, detail: str = "",
              actor_id: int | None = None) -> None:
    """Append-only processing/audit event. No-op when Mongo is disabled."""
    db = _connect()
    if db is None:
        return
    try:
        db.processing_events.insert_one({
            "incident_id": incident_id, "kind": kind, "detail": detail[:2000],
            "actor_id": actor_id, "created_at": _now(),
        })
    except Exception as e:
        log.warning("mongo log_event failed: %s", e)


def store_evidence_meta(evidence_id: int, incident_id: int, meta: dict) -> None:
    """CV/file metadata per evidence row (quality, mime, gps, sha...)."""
    db = _connect()
    if db is None:
        return
    try:
        db.evidence_meta.update_one(
            {"evidence_id": evidence_id},
            {"$set": {"incident_id": incident_id, "meta": dict(meta),
                      "updated_at": _now()},
             "$setOnInsert": {"created_at": _now()}},
            upsert=True,
        )
    except Exception as e:
        log.warning("mongo store_evidence_meta failed: %s", e)


def get_ai_history(incident_id: int, limit: int = 20) -> list[dict]:
    """AI run history for one incident, newest first. Empty when disabled."""
    db = _connect()
    if db is None:
        return []
    try:
        cur = db.ai_analyses.find({"incident_id": incident_id}) \
            .sort("created_at", -1).limit(max(1, min(limit, 100)))
        out = []
        for d in cur:
            d["id"] = str(d.pop("_id"))
            created = d.get("created_at")
            d["created_at"] = created.isoformat() if hasattr(created, "isoformat") else str(created)
            out.append(d)
        return out
    except Exception as e:
        log.warning("mongo get_ai_history failed: %s", e)
        return []


def get_events(incident_id: int, limit: int = 50) -> list[dict]:
    """Processing/audit events for one incident. Empty when disabled."""
    db = _connect()
    if db is None:
        return []
    try:
        cur = db.processing_events.find({"incident_id": incident_id}) \
            .sort("created_at", -1).limit(max(1, min(limit, 200)))
        out = []
        for d in cur:
            d["id"] = str(d.pop("_id"))
            created = d.get("created_at")
            d["created_at"] = created.isoformat() if hasattr(created, "isoformat") else str(created)
            out.append(d)
        return out
    except Exception as e:
        log.warning("mongo get_events failed: %s", e)
        return []
