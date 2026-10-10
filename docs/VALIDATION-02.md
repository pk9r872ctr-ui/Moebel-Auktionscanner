# Auftrag 02 · Prüfung und Ergebnis · 10.10.2026

## Ausgangslage und Umfang

Gemergter PR #1 auf `main`, Basiscommit `acb3011`. Alle vorhandenen Module,
Tests, Anforderungen, CI, Konfiguration und Dokumentation geprüft. Ausgangslauf:
28 Tests bestanden. Finanzkern und Demo erhalten; kein separates ERP berührt.

## Erreichte Funktionen

* Strenger JSON-/CSV-Vertrag mit Herkunft, Belegen, Beobachtungs-/Endzeit,
  Quelle/ID, Währung, Gebotsart und Gebührenmodell; keine stillen Finanzdefaults.
* Dubletten pro Quelle/ID, neuerer Stand gewinnt, Konflikte gesperrt.
* Atomarer Dateiimport, persistente SQLite-Beobachtungen, SHA-256-Idempotenz,
  Wiederanlauf und automatischer Watch-Modus für autorisierte Dateien.
* UI-Upload und Anzeige des Datei-Scanner-Speichers, klar von Demo getrennt.
* Vollständigkeits-/Aktualitätsprüfung vor dem vorhandenen Finanzkern.
* Private OIDC-Zugriffssperre und issuer/subject-Allowlist; lokale Entwicklung
  muss bewusst aktiviert werden. Standardbindung localhost, Telemetrie aus.
* Quellenrecherche, Datenmodell, zukünftige API, ERP-Grenze und iPhone-Anleitung.
  Manifest/Icon vorbereitet, kein eigenes umfangreiches Frontend.

## Nicht erreichte Funktionen / Blockaden

Keine Live-Abfrage: kein für diesen Scanner nutzbarer freigegebener Zugang
nachgewiesen. Siehe [SOURCES.md](SOURCES.md). Offizielle eBay-APIs sind dokumentiert,
aber Produktionszugang und passende Rechte wurden nicht bereitgestellt.
Es wurden keine Zugangssperren umgangen, Anbieter kontaktiert oder Dienste aktiviert.

Kein echter Nutzerexport wurde bereitgestellt. Die Importfunktion ist ausführbar
und getestet, aber ein fachlicher End-to-End-Abnahmetest mit berechtigten echten
Daten steht aus. Alle Prüfdatensätze waren explizit fiktiv (`TEST ONLY`, example.org).
Keine autonomen Käufe/Empfehlungen, ERP-Integration, Cloud-Persistenz, API-Endpunkte
oder produktiv installierte PWA. OIDC-Provider und iPhone/Safari-Abnahme fehlen.

## Tests

Python 3.12.14, Streamlit 1.65.0, pytest 8.4.2.

`python -m pytest -q`: **96 passed**, 2,48 Sekunden. `compileall`,
`pip check` und `git diff --check` bestanden. CI wird im neuen PR ausgeführt.

Automatisiert geprüft:

* Alle 28 bestehenden fachlichen/UI-Tests weiter bestanden.
* JSON/CSV, BOM und Dezimalkomma; Schema-/Größen-/Zeilenlimits; ungültige
  Zahlen, Zeitstempel, URLs, Versionen, Herkunft, Währungen und Datenfelder.
* NaN/Infinity, doppelte JSON-Schlüssel und verschachtelte ungültige Daten.
* Neueste Dublette, Konflikt, atomare Validierung und Speicher-Rollback.
* SQLite-Wiederanlauf/Idempotenz, Workspace-Trennung, keine ältere Überschreibung,
  kaputte Speicherinhalte, 0600-Neuanlage und Symlink-Abweisung.
* Scanner-Exitcodes und Mindestintervall; Fehler einer Datei isoliert.
  Watch-Modus verarbeitet geänderte Datei in einem zweiten Durchlauf und
  beendet sich bei Unterbrechung sauber.
* Sperren bei unbekannten Kosten/Preisen/Steuern, geschätzten Gebühren,
  abgelaufenen/alten Angeboten, Start-/Mindestpreis und anderer Gebührenbasis.
* Kalkulation mit losbezogenen Kosten statt Demo-Vorgaben.
* Private Voreinstellung, fehlende Konfiguration, falscher Zugriffsmodus,
  angemeldete erlaubte/falsche Identität und Login-Grenze ohne echten Provider.
* Streamlit-Importansicht und Worker-Speicher ohne Demo-Fallback.

Zusätzliche lokale Integration mit fiktiven Daten:

* CLI-Datei-Scanner: ein Testangebot eingefügt; späterer Lauf überspringt denselben
  Datei-Digest. Kein Netzwerkadapter ausgeführt.
* Playwright/Chromium: Testdatei im mobilen Upload importiert; manuell geprüftes
  Regelbesteuerungsszenario angezeigt; kaputte JSON-Datei kontrolliert abgewiesen,
  vorhandenes Worker-Angebot blieb sichtbar. Keine Browser-JavaScriptfehler.
* 390 × 844 und 320 × 568 Pixel: Dokumentbreite gleich Viewport, kein horizontaler
  Überlauf. Screenshot der Import-Karte geprüft. Kein echter Safari-Test.

Weitere Risiken und technische Schulden: [ARCHITECTURE.md](ARCHITECTURE.md).
Nächster Schritt: autorisierten echten Export und Quellenfreigabe beschaffen,
Vertragsabbildung abnehmen; danach genau einen read-only Live-Adapter entwickeln.
