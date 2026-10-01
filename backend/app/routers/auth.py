"""Auth router: register / login / refresh. Rate-limit via reverse proxy in prod (assumption)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas, security

router = APIRouter(prefix="/auth", tags=["auth"])

def _pub(u: models.User) -> dict:
    return {"id": u.id, "phone": u.phone, "full_name": u.full_name, "role": u.role}

@router.post("/register", status_code=201)
def register(body: schemas.RegisterIn, db: Session = Depends(get_db)):
    if db.query(models.User).filter_by(phone=body.phone).first():
        raise HTTPException(409, "Phone already registered")
    u = models.User(phone=body.phone, password_hash=security.hash_password(body.password),
                    full_name=body.full_name, role="driver")
    db.add(u); db.commit(); db.refresh(u)
    return {"user": _pub(u), "access": security.access_token(u.id), "refresh": security.refresh_token(u.id)}

@router.post("/login")
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    u = db.query(models.User).filter_by(phone=body.phone).first()
    if not u or not security.verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"user": _pub(u), "access": security.access_token(u.id), "refresh": security.refresh_token(u.id)}

@router.post("/refresh")
def refresh(token: str, db: Session = Depends(get_db)):
    try:
        uid = security.decode_token(token)
    except Exception:
        raise HTTPException(401, "Bad refresh token")
    u = db.get(models.User, uid)
    if not u: raise HTTPException(401, "Unknown user")
    return {"access": security.access_token(u.id)}
