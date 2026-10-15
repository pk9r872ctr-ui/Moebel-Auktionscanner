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
                           caption=lambda _: None, code=lambda *args, **kwargs: None,
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


# Only fabricated identities and configuration values are used below.
import pytest
import tomllib
from types import SimpleNamespace
import access

AUTH = {name: "configured-test-value" for name in
        ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")}
CLAIMS = {"iss": "https://accounts.google.com", "sub": "synthetic-owner-subject",
          "email": "never-display@example.org", "name": "NEVER DISPLAY NAME",
          "id_token": "NEVER_DISPLAY_TOKEN", "access_token": "NEVER_DISPLAY_ACCESS_TOKEN"}


class GateStopped(Exception):
    pass


def fake_gate(monkeypatch, *, identities=None, claims=None, logged_in=True, clicked=None):
    events = []
    secrets = {"auth": dict(AUTH), "scanner": {"allowed_identities": [] if identities is None else identities}}
    fake = SimpleNamespace(
        secrets=secrets, user=SimpleNamespace(is_logged_in=logged_in, to_dict=lambda: dict(CLAIMS if claims is None else claims)),
        button=lambda label: label == clicked,
        info=lambda msg: events.append(("info", msg)), error=lambda msg: events.append(("error", msg)),
        caption=lambda msg: events.append(("caption", msg)), code=lambda msg, **kw: events.append(("code", msg)),
        stop=lambda: (_ for _ in ()).throw(GateStopped()),
        login=lambda: events.append(("login", None)), logout=lambda: events.append(("logout", None)))
    monkeypatch.setenv("SCANNER_ACCESS_MODE", "private")
    monkeypatch.setattr(access, "st", fake)
    return fake, events


def test_empty_allowlist_allows_login_but_stops(monkeypatch):
    fake, events = fake_gate(monkeypatch, logged_in=False, clicked="Anmelden")
    with pytest.raises(GateStopped):
        access.enforce_access()
    assert ("login", None) in events
    assert not any(kind == "code" for kind, _ in events)
    assert fake.secrets["scanner"]["allowed_identities"] == []


@pytest.mark.parametrize("identities", [[], [{"issuer": CLAIMS["iss"], "subject": "other-user"}]])
def test_unapproved_identity_shows_only_safe_toml_then_stops(monkeypatch, identities):
    fake, events = fake_gate(monkeypatch, identities=identities)
    with pytest.raises(GateStopped):
        access.enforce_access()
    codes = [value for kind, value in events if kind == "code"]
    assert len(codes) == 1
    entry = tomllib.loads(codes[0])["scanner"]["allowed_identities"]
    assert entry == [{"issuer": CLAIMS["iss"], "subject": CLAIMS["sub"]}]
    displayed = str(events)
    for value in (CLAIMS['email'], CLAIMS['name'], CLAIMS['id_token'], CLAIMS['access_token'], AUTH['client_secret']):
        assert value not in displayed
    assert fake.secrets["scanner"]["allowed_identities"] == identities


@pytest.mark.parametrize("claims", [{}, {"iss": CLAIMS['iss']}, {"iss": "", "sub": ""}, {"iss": [], "sub": "x"}])
def test_missing_or_invalid_claims_never_enroll_or_authorize(monkeypatch, claims):
    _, events = fake_gate(monkeypatch, claims=claims)
    with pytest.raises(GateStopped):
        access.enforce_access()
    assert not any(kind == 'code' for kind, _ in events)


def test_claim_strings_cannot_inject_toml_tables():
    claims = {'iss': 'https://accounts.google.com', 'sub': 'quote"\n[[auth]]\nsecret="not-a-token"\t\\emoji😀'}
    snippet = access.identity_toml(claims)
    assert tomllib.loads(snippet) == {'scanner': {'allowed_identities': [{'issuer': claims['iss'], 'subject': claims['sub']}]}}


@pytest.mark.parametrize("identities", [None, {}, "", ["bad"], [{"issuer": "", "subject": "x"}]])
def test_malformed_allowlist_stays_closed_before_login(monkeypatch, identities):
    fake, events = fake_gate(monkeypatch, logged_in=False, clicked="Anmelden")
    fake.secrets['scanner']['allowed_identities'] = identities
    with pytest.raises(GateStopped):
        access.enforce_access()
    assert not any(kind in {'login', 'code'} for kind, _ in events)


def test_invalid_oauth_even_with_empty_allowlist_cannot_login(monkeypatch):
    fake, events = fake_gate(monkeypatch, logged_in=False, clicked='Anmelden')
    fake.secrets['auth']['client_secret'] = ''
    with pytest.raises(GateStopped):
        access.enforce_access()
    assert not any(kind == 'login' for kind, _ in events)


@pytest.mark.parametrize('authorized', [False, True])
def test_logout_stops_even_when_logout_function_returns(monkeypatch, authorized):
    identities = [{'issuer': CLAIMS['iss'], 'subject': CLAIMS['sub']}] if authorized else []
    _, events = fake_gate(monkeypatch, identities=identities, clicked='Abmelden')
    with pytest.raises(GateStopped):
        access.enforce_access()
    assert ('logout', None) in events


def test_app_empty_allowlist_blocks_dashboard_storage_and_imports(monkeypatch, tmp_path):
    import streamlit
    import scanner
    import imports
    import sources
    import registry
    monkeypatch.setenv('SCANNER_ACCESS_MODE', 'private')
    database = tmp_path / 'must-not-be-created.sqlite3'
    monkeypatch.setenv('SCANNER_DATABASE', str(database))
    monkeypatch.setattr(streamlit, 'user', SimpleNamespace(is_logged_in=True, to_dict=lambda: dict(CLAIMS)))
    def forbidden(*args, **kwargs):
        raise AssertionError('Business boundary crossed without manual approval')
    monkeypatch.setattr(scanner, 'ListingStore', forbidden)
    monkeypatch.setattr(imports, 'parse_import', forbidden)
    monkeypatch.setattr(sources, 'load_lots', forbidden)
    monkeypatch.setattr(registry, 'load_registry', forbidden)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py')
    app.secrets['auth'] = dict(AUTH)
    app.secrets['scanner'] = {'allowed_identities': []}
    app.run()
    assert not app.exception
    assert app.code and not app.title and not app.radio and not app.selectbox
    assert not app.get('file_uploader') and not app.get('download_button')
    assert not database.exists()
    assert tomllib.loads(app.code[0].value)['scanner']['allowed_identities'][0]['subject'] == CLAIMS['sub']


def test_manually_allowlisted_google_identity_can_enter_dashboard(monkeypatch):
    import streamlit
    monkeypatch.setenv('SCANNER_ACCESS_MODE', 'private')
    monkeypatch.setattr(streamlit, 'user', SimpleNamespace(is_logged_in=True, to_dict=lambda: dict(CLAIMS)))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py')
    app.secrets['auth'] = dict(AUTH)
    app.secrets['scanner'] = {'allowed_identities': [{'issuer': CLAIMS['iss'], 'subject': CLAIMS['sub']}]}
    app.run()
    assert not app.exception
    assert app.title and app.radio
    assert not app.code
