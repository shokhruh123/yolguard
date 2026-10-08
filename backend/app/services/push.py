"""Web Push отправка (VAPID). Без ключей — молча пропускаем, клиент на поллинге."""
from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from .. import models
from ..config import settings

log = logging.getLogger("yolguard.push")


def _configured() -> bool:
    return bool((settings.VAPID_PRIVATE_KEY or "").strip()
                and (settings.VAPID_PUBLIC_KEY or "").strip())


def send_to_user(db: Session, user_id: int, title: str, body: str,
                 url: str = "/app/") -> int:
    """Отправить push всем подпискам пользователя. Возвращает число доставленных.
    Протухшие подписки (404/410) удаляются."""
    subs = db.query(models.PushSubscription).filter_by(user_id=user_id).all()
    if not subs or not _configured():
        return 0
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        log.warning("pywebpush is not installed — push skipped")
        return 0
    import json as _json
    sent = 0
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s.endpoint,
                                   "keys": {"p256dh": s.p256dh, "auth": s.auth}},
                data=_json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY.strip(),
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
            sent += 1
        except Exception as e:
            # gone/invalid subscription -> drop it
            status = getattr(getattr(e, "response", None), "status_code", 0)
            if status in (404, 410) or "410" in str(e) or "404" in str(e):
                try:
                    db.delete(s); db.commit()
                except Exception:
                    db.rollback()
            else:
                log.warning("push to user %s failed: %s", user_id, e)
    return sent


def notify_participants(db: Session, incident_id: int, exclude_id: int,
                        title: str, body: str) -> int:
    """Разослать участникам инцидента кроме отправителя."""
    parts = db.query(models.Participant).filter_by(incident_id=incident_id).all()
    total = 0
    for p in parts:
        if p.user_id and p.user_id != exclude_id:
            try:
                total += send_to_user(db, p.user_id, title, body)
            except Exception as e:
                log.warning("notify failed: %s", e)
    return total
