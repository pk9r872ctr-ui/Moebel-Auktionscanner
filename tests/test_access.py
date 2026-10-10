from pathlib import Path
from streamlit.testing.v1 import AppTest
from access import allowed_identity


def test_identity_allowlist_uses_issuer_and_subject():
    allowed = [{"issuer": "https://identity.example.org", "subject": "internal-owner"}]
    assert allowed_identity({"iss": "https://identity.example.org", "sub": "internal-owner"}, allowed)
    assert not allowed_identity({"iss": "https://other.example.org", "sub": "internal-owner"}, allowed)
    assert not allowed_identity({"email": "owner@example.org"}, allowed)
    assert not allowed_identity({}, [])


def test_private_missing_config_fails_closed(monkeypatch):
    monkeypatch.setenv("SCANNER_ACCESS_MODE", "private")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    assert not app.exception
    assert any("Zugriff gesperrt" in error.value for error in app.error)
    assert not app.radio
    assert not app.selectbox


def test_invalid_mode_fails_closed(monkeypatch):
    monkeypatch.setenv("SCANNER_ACCESS_MODE", "public")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    assert not app.exception
    assert not app.radio


def test_default_is_private(monkeypatch):
    monkeypatch.delenv("SCANNER_ACCESS_MODE", raising=False)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    assert not app.exception
    assert not app.radio
    assert any("Zugriff gesperrt" in error.value for error in app.error)


def test_private_gate_authorized_wrong_and_logged_out(monkeypatch):
    from types import SimpleNamespace
    import access
    import pytest
    monkeypatch.setenv("SCANNER_ACCESS_MODE", "private")
    class Stopped(Exception):
        pass
    events = []
    secrets = {"auth": {name: "configured-test-value" for name in
               ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")},
               "scanner": {"allowed_identities": [{"issuer": "test-issuer", "subject": "test-owner"}]}}
    user = SimpleNamespace(is_logged_in=True, to_dict=lambda: {"iss": "test-issuer", "sub": "test-owner"})
    fake = SimpleNamespace(secrets=secrets, user=user, button=lambda _: False,
                           error=lambda msg: events.append(msg), info=lambda msg: events.append(msg),
                           stop=lambda: (_ for _ in ()).throw(Stopped()),
                           login=lambda: events.append("login"), logout=lambda: events.append("logout"))
    monkeypatch.setattr(access, "st", fake)
    access.enforce_access()
    assert not events
    user.to_dict = lambda: {"iss": "test-issuer", "sub": "other-user"}
    with pytest.raises(Stopped):
        access.enforce_access()
    assert "nicht freigegeben" in events[-1]
    user.is_logged_in = False
    fake.button = lambda _: True
    with pytest.raises(Stopped):
        access.enforce_access()
    assert events[-1] == "login"
