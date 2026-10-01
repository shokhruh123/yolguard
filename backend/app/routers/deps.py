"""Auth dependency + incident/vehicle/review flows."""
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, security


def user_from_token(token: str, db: Session) -> models.User:
    """Resolve a bearer token string to a User, or raise 401."""
    try:
        uid = security.decode_token(token)
    except Exception:
        raise HTTPException(401, "Invalid token")
    u = db.get(models.User, uid)
    if not u:
        raise HTTPException(401, "Unknown user")
    return u


def current_user(authorization: str = Header(""), db: Session = Depends(get_db)) -> models.User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    return user_from_token(authorization[7:], db)


def need_role(*roles: str):
    def dep(u: models.User = Depends(current_user)):
        if u.role not in roles and u.role != "admin":
            raise HTTPException(403, "Forbidden for role " + u.role)
        return u
    return dep
