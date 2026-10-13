import logging

import pytest

from app.core import security


@pytest.fixture(autouse=True)
def valid_config(monkeypatch):
    monkeypatch.setattr(security, "JWT_SECRET", "s" * 48)
    monkeypatch.setattr(security, "API_KEY", "")


def test_valid_config_passes(caplog):
    with caplog.at_level(logging.WARNING, logger="lynceus.security"):
        security.validate_startup_config()
    assert "LYNCEUS_API_KEY is not set" in caplog.text


def test_missing_jwt_secret_refuses_to_start(monkeypatch):
    monkeypatch.setattr(security, "JWT_SECRET", "")
    with pytest.raises(RuntimeError):
        security.validate_startup_config()


def test_short_jwt_secret_refuses_to_start(monkeypatch):
    monkeypatch.setattr(security, "JWT_SECRET", "short")
    with pytest.raises(RuntimeError):
        security.validate_startup_config()


def test_short_api_key_refuses_to_start(monkeypatch):
    monkeypatch.setattr(security, "API_KEY", "tooshort")
    with pytest.raises(RuntimeError):
        security.validate_startup_config()


def test_strong_api_key_is_accepted(monkeypatch, caplog):
    monkeypatch.setattr(security, "API_KEY", "k" * 24)
    with caplog.at_level(logging.WARNING, logger="lynceus.security"):
        security.validate_startup_config()
    assert caplog.text == ""


def test_ws_key_check_with_no_key_configured():
    assert security.verify_ws_key("") is True
    assert security.verify_ws_key("anything") is True


def test_ws_key_check_with_key_configured(monkeypatch):
    monkeypatch.setattr(security, "API_KEY", "k" * 24)
    assert security.verify_ws_key("k" * 24) is True
    assert security.verify_ws_key("wrong") is False
    assert security.verify_ws_key("") is False