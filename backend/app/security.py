"""Password hashing via stdlib PBKDF2 (no native deps) + JWT access/refresh."""
import hashlib, secrets
from datetime import datetime, timedelta
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

def _token(sub: str, minutes: int) -> str:
    exp = datetime.utcnow() + timedelta(minutes=minutes)
    return jwt.encode({"sub": sub, "exp": exp}, settings.SECRET_KEY, algorithm=ALG)

def access_token(user_id: int) -> str:
    return _token(str(user_id), settings.ACCESS_TOKEN_MINUTES)

def refresh_token(user_id: int) -> str:
    return _token(str(user_id), settings.REFRESH_TOKEN_DAYS * 24 * 60)

def decode_token(t: str) -> int:
    return int(jwt.decode(t, settings.SECRET_KEY, algorithms=[ALG])["sub"])
