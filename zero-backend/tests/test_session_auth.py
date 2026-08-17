import pytest

from core.session_auth import (
    SessionConfigurationError,
    create_session_credentials,
    verify_session_token,
)


def test_session_token_is_bound_to_session(monkeypatch):
    monkeypatch.setenv("CHAT_SESSION_SECRET", "s" * 32)
    credentials = create_session_credentials(now=1_000)
    assert verify_session_token(credentials.session_id, credentials.token, now=1_001)
    other = create_session_credentials(now=1_000)
    assert not verify_session_token(other.session_id, credentials.token, now=1_001)


def test_session_token_expires(monkeypatch):
    monkeypatch.setenv("CHAT_SESSION_SECRET", "s" * 32)
    credentials = create_session_credentials(now=1_000)
    assert not verify_session_token(credentials.session_id, credentials.token, now=100_000)


def test_session_secret_must_be_configured(monkeypatch):
    monkeypatch.delenv("CHAT_SESSION_SECRET", raising=False)
    monkeypatch.delenv("TELEMETRY_HASH_SALT", raising=False)
    with pytest.raises(SessionConfigurationError):
        create_session_credentials()
