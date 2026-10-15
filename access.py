"""Optional private OIDC gate; local mode is explicitly not cloud-safe."""
import os
import json
from collections.abc import Mapping
import streamlit as st


def allowed_identity(claims, identities):
    """Use immutable OIDC issuer+subject, never an unverified email claim."""
    issuer, subject = claims.get("iss"), claims.get("sub")
    return isinstance(issuer, str) and bool(issuer.strip()) and isinstance(subject, str) and bool(subject.strip()) and any(
        isinstance(entry, Mapping) and entry.get("issuer") == issuer
        and entry.get("subject") == subject for entry in identities)


def identity_toml(claims):
    """Display only issuer/subject, quoted as TOML basic strings (no raw claims)."""
    issuer, subject = claims.get("iss"), claims.get("sub")
    if any(not isinstance(value, str) or not value.strip() or len(value) > 2000
           for value in (issuer, subject)):
        return None
    return ("[[scanner.allowed_identities]]\n"
            f"issuer = {json.dumps(issuer, ensure_ascii=False)}\n"
            f"subject = {json.dumps(subject, ensure_ascii=False)}\n")


def enforce_access():
    mode = os.environ.get("SCANNER_ACCESS_MODE", "private")
    if mode == "local":
        st.caption("Lokaler Entwicklungsmodus ohne Zugriffsschutz – nicht öffentlich betreiben.")
        return
    if mode != "private":
        st.error("Ungültiger Zugriffsmodus. Zugriff gesperrt.")
        st.stop()
    try:
        auth = st.secrets["auth"]
        identities = st.secrets["scanner"]["allowed_identities"]
        if not isinstance(identities, list) or any(
            not isinstance(entry, Mapping)
            or any(not isinstance(entry.get(key), str) or not entry[key].strip()
                   for key in ("issuer", "subject")) for entry in identities):
            raise ValueError
        if not isinstance(auth, Mapping):
            raise ValueError
        ready = all(isinstance(auth.get(key), str) and auth[key].strip()
                    for key in ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url"))
        if not ready:
            raise ValueError
    except (KeyError, FileNotFoundError, ValueError, TypeError):
        st.error("Privater Zugriff nicht vollständig konfiguriert. Zugriff gesperrt.")
        st.stop()
    if not st.user.is_logged_in:
        st.info("Privater Scanner: Anmeldung erforderlich.")
        if st.button("Anmelden"):
            st.login()
        st.stop()
    claims = st.user.to_dict()
    if not allowed_identity(claims, identities):
        st.error("Dieses Konto ist für den internen Scanner nicht freigegeben.")
        configuration = identity_toml(claims)
        if configuration is not None:
            st.caption("Manuelle Freigabe: Dieser TOML-Eintrag enthält ausschließlich iss und sub "
                       "als issuer und subject. In den privaten Secrets das bisherige "
                       "allowed_identities = [] ersetzen; vorhandene Einträge erhalten. "
                       "Bis zur manuellen Freigabe bleiben alle Geschäftsdaten gesperrt.")
            st.code(configuration, language="toml")
        if st.button("Abmelden"):
            st.logout()
        st.stop()
    if st.button("Abmelden"):
        st.logout()
        st.stop()
