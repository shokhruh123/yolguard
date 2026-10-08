"""Web Push подписки + публичный VAPID-ключ для Service Worker."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from ..config import settings
from .deps import current_user

router = APIRouter(prefix="/push", tags=["push"])

@router.get("/vapid-key")
def vapid_key():
    return {"publicKey": settings.VAPID_PUBLIC_KEY or ""}

@router.post("/subscribe", status_code=201)
def subscribe(body: schemas.PushSubIn, db: Session = Depends(get_db),
              u: models.User = Depends(current_user)):
    s = db.query(models.PushSubscription).filter_by(endpoint=body.endpoint).first()
    if s:
        s.user_id, s.p256dh, s.auth = u.id, body.keys.p256dh, body.keys.auth
    else:
        db.add(models.PushSubscription(user_id=u.id, endpoint=body.endpoint,
                                       p256dh=body.keys.p256dh, auth=body.keys.auth))
    db.commit()
    return {"subscribed": True}

@router.post("/unsubscribe")
def unsubscribe(body: schemas.PushSubIn, db: Session = Depends(get_db),
                u: models.User = Depends(current_user)):
    db.query(models.PushSubscription).filter_by(endpoint=body.endpoint,
                                                user_id=u.id).delete()
    db.commit()
    return {"subscribed": False}
