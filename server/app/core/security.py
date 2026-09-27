from fastapi import Depends, Header, HTTPException, status

from app.config import API_KEY, JWT_SECRET

MIN_KEY_LENGTH = 16
MIN_JWT_SECRET_LENGTH = 32


def validate_startup_config() -> None:
    import logging

    logger = logging.getLogger("lynceus.security")

    if not API_KEY:
        logger.warning("LYNCEUS_API_KEY is not set — agent metrics ingestion is running with no authentication")
    elif len(API_KEY) < MIN_KEY_LENGTH:
        raise RuntimeError(
            f"LYNCEUS_API_KEY is set but only {len(API_KEY)} characters long "
            f"(minimum {MIN_KEY_LENGTH}) — refusing to start with a weak key"
        )

    if not JWT_SECRET:
        raise RuntimeError("LYNCEUS_JWT_SECRET is not set — refusing to start without a signing secret for user sessions")

    if len(JWT_SECRET) < MIN_JWT_SECRET_LENGTH:
        raise RuntimeError(
            f"LYNCEUS_JWT_SECRET is only {len(JWT_SECRET)} characters long "
            f"(minimum {MIN_JWT_SECRET_LENGTH}) — refusing to start with a weak secret"
        )


def verify_ws_key(key: str) -> bool:
    if not API_KEY:
        return True
    return key == API_KEY


def require_user(authorization: str = Header(default="")) -> dict:
    from app.core.auth import decode_access_token

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing or invalid access token")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired access token")

    return payload


def require_admin(user: dict = Depends(require_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    return user

# agent metrics ingestion (WebSocket) still authenticates via LYNCEUS_API_KEY through verify_ws_key.
# dashboard/human routes authenticate via JWT access tokens through require_user / require_admin.
# to bootstrap the first admin account, set LYNCEUS_ADMIN_USERNAME and LYNCEUS_ADMIN_PASSWORD
# before starting the server for the first time.