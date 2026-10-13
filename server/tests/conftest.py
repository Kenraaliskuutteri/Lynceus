import os
import shutil
import tempfile
from datetime import datetime, timezone

for _key in [k for k in os.environ if k.startswith("LYNCEUS_")]:
    del os.environ[_key]

WORKDIR = tempfile.mkdtemp(prefix="lynceus-tests-")
os.environ["LYNCEUS_DB_URL"] = f"sqlite:///{WORKDIR}/test.db"
os.environ["LYNCEUS_JWT_SECRET"] = "t" * 48

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_access_token, hash_password
from app.core.database import Base, SessionLocal, engine
from app.core.migrate import run_migrations
from app.main import app
from app.models.user import User


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    run_migrations()
    yield
    engine.dispose()
    shutil.rmtree(WORKDIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app, base_url="https://testserver")


def make_user(db, username="admin", password="secret-pass", role="admin"):
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        failed_attempts=0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_headers(db):
    user = make_user(db, "admin", "admin-pass", "admin")
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@pytest.fixture
def viewer_headers(db):
    user = make_user(db, "viewer", "viewer-pass", "viewer")
    return {"Authorization": f"Bearer {create_access_token(user)}"}