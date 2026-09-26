from fastapi import Header, HTTPException, status

from app.config import API_KEY

MIN_KEY_LENGTH = 16


def validate_startup_config() -> None:
    import logging

    logger = logging.getLogger("lynceus.security")

    if not API_KEY:
        logger.warning("LYNCEUS_API_KEY is not set — the API and WebSocket are running with no authentication")
        return

    if len(API_KEY) < MIN_KEY_LENGTH:
        raise RuntimeError(
            f"LYNCEUS_API_KEY is set but only {len(API_KEY)} characters long "
            f"(minimum {MIN_KEY_LENGTH}) — refusing to start with a weak key"
        )


def verify_api_key(authorization: str = Header(default="")) -> None:
    if not API_KEY:
        return
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or missing api key")


def verify_ws_key(key: str) -> bool:
    if not API_KEY:
        return True
    return key == API_KEY

# to use this run: export LYNCEUS_API_KEY=<some-long-random-string> before starting your server