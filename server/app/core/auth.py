import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.orm import Session

from app.config import (
    JWT_SECRET,
    JWT_ACCESS_MINUTES,
    JWT_REFRESH_DAYS,
    LOGIN_MAX_ATTEMPTS,
    LOGIN_LOCKOUT_MINUTES,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken

hasher = PasswordHasher()
_DUMMY_HASH = hasher.hash("dummy-password-for-constant-time-unknown-user")


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_ACCESS_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_refresh_token(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            created_at=now,
            expires_at=now + timedelta(days=JWT_REFRESH_DAYS),
        )
    )
    db.commit()

    return raw_token


def rotate_refresh_token(db: Session, raw_token: str):
    now = datetime.now(timezone.utc)

    record = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_token(raw_token)).first()
    if record is None or record.revoked_at is not None:
        return None

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        return None

    user = db.get(User, record.user_id)
    if user is None:
        return None

    record.revoked_at = now
    new_raw_token = issue_refresh_token(db, user)

    return user, new_raw_token


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    record = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_token(raw_token)).first()
    if record is not None and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        db.commit()


def revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    now = datetime.now(timezone.utc)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    ).update({RefreshToken.revoked_at: now})
    db.commit()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    now = datetime.now(timezone.utc)
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None

    locked_until = user.locked_until
    if locked_until is not None:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            return None

    if not verify_password(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= LOGIN_MAX_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
            user.failed_attempts = 0
        db.commit()
        return None

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()

    return user


def seed_admin_user(db: Session) -> None:
    from app.config import ADMIN_BOOTSTRAP_USERNAME, ADMIN_BOOTSTRAP_PASSWORD

    if db.query(User).count() > 0:
        return
    if not ADMIN_BOOTSTRAP_USERNAME or not ADMIN_BOOTSTRAP_PASSWORD:
        return

    db.add(
        User(
            username=ADMIN_BOOTSTRAP_USERNAME,
            password_hash=hash_password(ADMIN_BOOTSTRAP_PASSWORD),
            role="admin",
            failed_attempts=0,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()