import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import (
    authenticate_user,
    create_access_token,
    issue_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
)
from app.core.database import get_db
from app.core.security import require_user

router = APIRouter()

REFRESH_COOKIE_NAME = "lynceus_refresh"
CSRF_COOKIE_NAME = "lynceus_csrf"
REFRESH_COOKIE_PATH = "/api/v1/auth"
CSRF_COOKIE_PATH = "/"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    username: str
    role: str


def _set_session_cookies(response: Response, refresh_token: str) -> None:
    csrf_token = secrets.token_urlsafe(32)

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="strict",
        path=CSRF_COOKIE_PATH,
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE_NAME, path=CSRF_COOKIE_PATH)


def _verify_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf token mismatch")


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")

    access_token = create_access_token(user)
    refresh_token = issue_refresh_token(db, user)
    _set_session_cookies(response, refresh_token)

    return LoginResponse(access_token=access_token, username=user.username, role=user.role)


@router.post("/auth/refresh", response_model=LoginResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    _verify_csrf(request)

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing refresh token")

    result = rotate_refresh_token(db, raw_token)
    if result is None:
        _clear_session_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired refresh token")

    user, new_raw_token = result
    access_token = create_access_token(user)
    _set_session_cookies(response, new_raw_token)

    return LoginResponse(access_token=access_token, username=user.username, role=user.role)


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    _verify_csrf(request)

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        revoke_refresh_token(db, raw_token)

    _clear_session_cookies(response)
    return {"detail": "logged out"}


@router.get("/auth/me")
def me(user: dict = Depends(require_user)):
    return {"username": user.get("username"), "role": user.get("role")}