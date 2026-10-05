"""Password hashing via stdlib PBKDF2 (no native deps) + JWT access/refresh."""
import hashlib, secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
from .config import settings

ALG = "HS256"
ITER = 200_000

def hash_password(p: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), ITER).hex()
    return f"pbkdf2${ITER}${salt}${h}"

def verify_password(p: str, h: str) -> bool:
    try:
        _, it, salt, hexh = h.split("$")
        ch = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), int(it)).hex()
        return secrets.compare_digest(ch, hexh)
    except Exception:
        return False

def _token(sub: str, minutes: int, typ: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": sub, "exp": exp, "typ": typ}, settings.SECRET_KEY, algorithm=ALG)

def access_token(user_id: int) -> str:
    return _token(str(user_id), settings.ACCESS_TOKEN_MINUTES, "access")

def refresh_token(user_id: int) -> str:
    return _token(str(user_id), settings.REFRESH_TOKEN_DAYS * 24 * 60, "refresh")

def decode_token(t: str, expect: str | None = None) -> int:
    """Decode JWT -> user id. Legacy tokens without 'typ' are accepted when
    expect is None (backwards compatible); new code passes expect explicitly."""
    data = jwt.decode(t, settings.SECRET_KEY, algorithms=[ALG])
    if expect is not None and "typ" in data and data["typ"] != expect:
        raise ValueError(f"wrong token type: expected {expect}")
    return int(data["sub"])
