from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt as _bcrypt
from jose import JWTError, jwt

_lock  = threading.Lock()
logger = logging.getLogger(__name__)

from src.security import UserContext

SECRET_KEY      = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM       = "HS256"
TOKEN_TTL_HOURS = 24
ADMIN_USERNAME  = "admin"

USERS_FILE = Path(__file__).parent / "users.json"


def _hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())


def _load() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text())
    except json.JSONDecodeError:
        logger.error("users.json is malformed — returning empty user store")
        return {}


def _save(users: dict) -> None:
    tmp = USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, indent=2))
    tmp.replace(USERS_FILE)


def ensure_default_admin() -> None:
    with _lock:
        users = _load()
        if ADMIN_USERNAME not in users:
            password = os.getenv("ADMIN_PASSWORD", "admin123")
            if password == "admin123":
                logger.warning("SECURITY: Admin password is the default 'admin123' — set ADMIN_PASSWORD in .env")
            users[ADMIN_USERNAME] = {"hashed_password": _hash(password)}
            _save(users)
            logger.info("Created default admin user")


def authenticate_user(username: str, password: str) -> UserContext | None:
    users = _load()
    data  = users.get(username)
    if not data or not _verify(password, data["hashed_password"]):
        return None
    return UserContext(user_id=username)


def create_access_token(user: UserContext) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    return jwt.encode(
        {"sub": user.user_id, "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM,
    )


def decode_token(token: str) -> UserContext | None:
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        return UserContext(user_id=username)
    except (JWTError, ValueError):
        return None


def list_users() -> list[str]:
    return list(_load().keys())


def create_user(username: str, password: str) -> bool:
    with _lock:
        users = _load()
        if username in users:
            return False
        users[username] = {"hashed_password": _hash(password)}
        _save(users)
        return True


def delete_user(username: str) -> bool:
    with _lock:
        users = _load()
        if username not in users or username == ADMIN_USERNAME:
            return False
        del users[username]
        _save(users)
        return True
