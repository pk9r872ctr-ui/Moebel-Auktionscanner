import pytest


@pytest.fixture(autouse=True)
def local_test_mode(monkeypatch):
    # No identity provider configured in unit tests. Private-gate tests override.
    monkeypatch.setenv("SCANNER_ACCESS_MODE", "local")
