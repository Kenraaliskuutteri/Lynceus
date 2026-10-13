from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app import config
from app.core.auth import (
    issue_refresh_token,
    revoke_all_refresh_tokens,
    rotate_refresh_token,
    seed_admin_user,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from conftest import make_user


def login(client, username="admin", password="secret-pass"):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_login_returns_token_role_and_cookies(client, db):
    make_user(db, "admin", "secret-pass", "admin")
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "admin"
    assert body["role"] == "admin"
    assert body["access_token"]
    assert response.cookies["lynceus_refresh"]
    assert response.cookies["lynceus_csrf"]


def test_login_rejects_wrong_password(client, db):
    make_user(db)
    assert login(client, password="wrong").status_code == 401


def test_login_rejects_unknown_user(client):
    assert login(client, username="nobody").status_code == 401


def test_lockout_after_repeated_failures(client, db, monkeypatch):
    monkeypatch.setattr("app.core.auth.LOGIN_MAX_ATTEMPTS", 3)
    make_user(db)
    for _ in range(3):
        assert login(client, password="wrong").status_code == 401
    assert login(client).status_code == 401

    db.expire_all()
    user = db.query(User).filter(User.username == "admin").one()
    assert user.locked_until is not None
    user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert login(client).status_code == 200


def test_successful_login_resets_failed_attempts(client, db, monkeypatch):
    monkeypatch.setattr("app.core.auth.LOGIN_MAX_ATTEMPTS", 3)
    make_user(db)
    login(client, password="wrong")
    login(client, password="wrong")
    assert login(client).status_code == 200
    db.expire_all()
    assert db.query(User).one().failed_attempts == 0


def test_me_returns_identity(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == {"username": "admin", "role": "admin"}


@pytest.mark.parametrize("path", ["/api/v1/servers", "/api/v1/alerts", "/api/v1/alerts/config"])
def test_protected_routes_require_token(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer garbage"}).status_code == 401


def encode(payload, secret=None):
    return jwt.encode(payload, secret or config.JWT_SECRET, algorithm="HS256")


def access_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "username": "admin",
        "role": "admin",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "type": "access",
    }
    payload.update(overrides)
    return payload


def test_expired_token_rejected(client):
    token = encode(access_payload(exp=datetime.now(timezone.utc) - timedelta(minutes=1)))
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_with_wrong_type_rejected(client):
    token = encode(access_payload(type="refresh"))
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_signed_with_other_secret_rejected(client):
    token = encode(access_payload(), secret="x" * 48)
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("patch", "/api/v1/servers/s1/thresholds", {"cpuUsage": 70}),
        ("post", "/api/v1/alerts/1/acknowledge", None),
        ("post", "/api/v1/alerts/1/unacknowledge", None),
        ("post", "/api/v1/alerts/test-webhook", None),
    ],
)
def test_viewer_cannot_use_admin_routes(client, viewer_headers, method, path, body):
    response = client.request(method.upper(), path, headers=viewer_headers, json=body)
    assert response.status_code == 403


def test_refresh_issues_new_access_token(client, db):
    make_user(db)
    csrf = login(client).cookies["lynceus_csrf"]
    response = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_requires_matching_csrf(client, db):
    make_user(db)
    login(client)
    assert client.post("/api/v1/auth/refresh").status_code == 403
    assert client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "wrong"}).status_code == 403


def test_logout_revokes_refresh_token(client, db):
    make_user(db)
    response = login(client)
    raw = response.cookies["lynceus_refresh"]
    csrf = response.cookies["lynceus_csrf"]
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert rotate_refresh_token(db, raw) is None


def test_refresh_token_is_single_use(db):
    user = make_user(db)
    raw = issue_refresh_token(db, user)
    assert rotate_refresh_token(db, raw) is not None
    assert rotate_refresh_token(db, raw) is None


def test_expired_refresh_token_rejected(db):
    user = make_user(db)
    raw = issue_refresh_token(db, user)
    record = db.query(RefreshToken).one()
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert rotate_refresh_token(db, raw) is None


def test_revoke_all_refresh_tokens(db):
    user = make_user(db)
    first = issue_refresh_token(db, user)
    second = issue_refresh_token(db, user)
    revoke_all_refresh_tokens(db, user.id)
    assert rotate_refresh_token(db, first) is None
    assert rotate_refresh_token(db, second) is None


def test_seed_admin_creates_user_when_empty(db, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_BOOTSTRAP_USERNAME", "boss")
    monkeypatch.setattr(config, "ADMIN_BOOTSTRAP_PASSWORD", "boss-pass")
    seed_admin_user(db)
    user = db.query(User).one()
    assert user.username == "boss"
    assert user.role == "admin"


def test_seed_admin_skips_when_users_exist(db, monkeypatch):
    make_user(db, "existing", "pw", "viewer")
    monkeypatch.setattr(config, "ADMIN_BOOTSTRAP_USERNAME", "boss")
    monkeypatch.setattr(config, "ADMIN_BOOTSTRAP_PASSWORD", "boss-pass")
    seed_admin_user(db)
    assert db.query(User).count() == 1


def test_seed_admin_skips_without_credentials(db, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_BOOTSTRAP_USERNAME", "")
    monkeypatch.setattr(config, "ADMIN_BOOTSTRAP_PASSWORD", "")
    seed_admin_user(db)
    assert db.query(User).count() == 0