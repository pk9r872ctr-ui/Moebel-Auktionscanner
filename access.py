"""Optional private OIDC gate; local mode is explicitly not cloud-safe."""
import os
from collections.abc import Mapping
import streamlit as st


def allowed_identity(claims, identities):
    """Use immutable OIDC issuer+subject, never an unverified email claim."""
    issuer, subject = claims.get("iss"), claims.get("sub")
    return isinstance(issuer, str) and isinstance(subject, str) and any(
        isinstance(entry, Mapping) and entry.get("issuer") == issuer
        and entry.get("subject") == subject for entry in identities)


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
        identities = list(st.secrets["scanner"]["allowed_identities"])
        ready = all(auth.get(key) for key in ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url"))
        if not ready or not identities:
            raise ValueError
    except (KeyError, FileNotFoundError, ValueError, TypeError):
        st.error("Privater Zugriff nicht vollständig konfiguriert. Zugriff gesperrt.")
        st.stop()
    if not st.user.is_logged_in:
        st.info("Privater Scanner: Anmeldung erforderlich.")
        if st.button("Anmelden"):
            st.login()
        st.stop()
    if not allowed_identity(st.user.to_dict(), identities):
        st.error("Dieses Konto ist für den internen Scanner nicht freigegeben.")
        if st.button("Abmelden"):
            st.logout()
        st.stop()
    if st.button("Abmelden"):
        st.logout()
