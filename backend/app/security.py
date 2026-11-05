import base64
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from .config import get_settings

_ph = PasswordHasher()

def hash_password(p: str) -> str:
    return _ph.hash(p)

def verify_password(h: str, p: str) -> bool:
    try:
        return _ph.verify(h, p)
    except (VerifyMismatchError, Exception):
        return False

def _key() -> str:
    k = get_settings().secret_key
    if len(k) < 32:
        raise RuntimeError("SECRET_KEY must be configured and be at least 32 characters long.")
    return k

def make_access(user_id: int, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=get_settings().access_minutes)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "exp": exp},
        _key(),
        algorithm="HS256"
    )

def decode_access(t: str) -> dict:
    return jwt.decode(t, _key(), algorithms=["HS256"])

def new_refresh() -> tuple[str, str]:
    t = secrets.token_urlsafe(48)
    return t, hashlib.sha256(t.encode()).hexdigest()

def hash_refresh(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()

def _fernet() -> Fernet:
    # Derive a 32-byte urlsafe key from the application secret_key
    derived = base64.urlsafe_b64encode(hashlib.sha256(_key().encode()).digest())
    return Fernet(derived)

def encrypt(s: str) -> str:
    if not s:
        return ""
    return _fernet().encrypt(s.encode("utf-8")).decode("utf-8")

def decrypt(s: str) -> str:
    if not s:
        return ""
    try:
        return _fernet().decrypt(s.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""

_hits: dict[str, list[float]] = {}

def rate_limited(key: str, limit: int = 10, window: int = 60) -> bool:
    now_ts = time.time()
    history = [t for t in _hits.get(key, []) if now_ts - t < window]
    history.append(now_ts)
    _hits[key] = history
    return len(history) > limit

