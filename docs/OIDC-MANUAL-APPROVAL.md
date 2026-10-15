# Google-OIDC: Anmeldung und manuelle Identitätsfreigabe

Prüfung am 15.10.2026 im Repository `v7nc35/Moebel-Auktionscanner`,
Ausgangscommit `ceaff73`. Vor Änderung: 182 Tests bestanden.

## Verhalten

Eine vollständige bestehende OIDC-Konfiguration erlaubt jetzt auch bei
`scanner.allowed_identities = []` die Anmeldung über `st.login()`.
Streamlit übernimmt weiterhin den OIDC-Ablauf und die Prüfung der Anmeldung.
Es gibt keinen zusätzlichen Loginpfad oder automatische Benutzerfreigabe.

Nach Anmeldung sieht ein nicht freigegebenes Konto nur die Sperrmeldung,
einen TOML-Eintrag aus `iss` und `sub` sowie die Abmeldemöglichkeit. E-Mail,
Name, Tokens, weitere Claims und OAuth-Secrets werden nicht ausgegeben.
Fehlende/ungültige Identitätsclaims ergeben keinen Freigabeeintrag.

`app.py` ruft `enforce_access()` weiterhin vor Dashboard, Datenbankzugriff,
Quellenanzeige und Import-/Exportfunktionen auf. Der nicht autorisierte
Zweig endet immer mit `st.stop()`. Auch nach Abmelden wird gestoppt.
Freigegeben wird ausschließlich durch den vorhandenen exakten Vergleich von
OIDC-Issuer und Subject mit manuell gepflegten Secrets. Unvollständige OAuth-
Konfiguration und fehlerhafte Allowlist-Strukturen bleiben gesperrt.
Der vorhandene explizite lokale Entwicklungsmodus bleibt unverändert.

## Manuelle Freigabe

1. Bei leerer Allowlist anmelden. Die Anwendung bleibt gesperrt.
2. Den angezeigten Issuer und Subject mit der beabsichtigten Identität prüfen.
3. In den privaten Streamlit-Secrets das bisherige `allowed_identities = []`
   entfernen und den angezeigten `[[scanner.allowed_identities]]`-Eintrag
   übernehmen. Bestehende freigegebene Einträge erhalten. OAuth-Konfiguration
   nicht ersetzen. Secrets und echte Identitätswerte nicht in Git committen.
4. Nach Übernahme der Secrets die Sitzung neu laden. Erst der passende
   manuelle Allowlist-Eintrag gibt das Dashboard frei.

Die Anwendung schreibt oder verändert keine Secrets. Der TOML-Code wird mit
korrekter Zeichenmaskierung erzeugt; Anführungszeichen, Zeilenumbrüche und
Unicode können keine zusätzlichen TOML-Tabellen einschleusen. Anmeldung
allein erteilt keine Zugriffsberechtigung.

## Abnahme und Grenzen

Python 3.12.14, Streamlit 1.65.0, pytest 8.4.2.

- `python -m pytest tests/test_access.py -q`: **23 bestanden**.
- `python -m pytest -q`: **200 bestanden, 0 fehlgeschlagen**.
- `python -m pip check`, Kompilierung von `access.py`, `app.py` und Auth-Tests
  sowie `git diff --check`: bestanden.

Neue Prüfungen: Loginaufruf bei leerer Allowlist; Sperre nach Anmeldung;
leere/falsche/fehlerhafte Allowlist; fehlende Claims; manuelle Freigabe eines
synthetischen Google-Issuer/Subject-Paars; Ausgabe ausschließlich der beiden
Kennungen ohne weitere Claims/Secrets; TOML-Roundtrip und Injection-Zeichen;
Abmelden; unvollständiges OAuth; unveränderte Allowlist.

Streamlit-AppTest prüft die tatsächliche `app.py` mit synthetischem angemeldetem
Nutzer und leerer Allowlist. Datenbank-, Import-, Demo- und Registeraufrufe
sind als verbotene Aufrufe instrumentiert: keine Dashboard-/Upload-/Download-
Elemente, keine Datenbankanlage und kein Geschäftsdatenzugriff.
Mit manuell passender Allowlist wird das Dashboard wieder erreichbar.

Kein tatsächlicher Google-OIDC-Roundtrip und keine Prüfung produktiver Secrets:
Tests verwenden ausschließlich synthetische Konfiguration und Identitäten.
Die bestehende Hosting-/Providerkonfiguration muss der Eigentümer separat
prüfen. Keine Secrets gelesen, geändert oder veröffentlicht; keine
Versions-/Abhängigkeits-/Datenvertragsänderung, kein Deployment, kein Auto-Merge
und keine zusätzlichen Dienste oder Kosten.
