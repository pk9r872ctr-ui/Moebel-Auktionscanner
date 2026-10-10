# Prüfprotokoll · 10.10.2026

## Vollständige Ausgangsprüfung

Alle sechs vorhandenen Repository-Dateien gelesen (`app.py`, `scoring.py`,
`sources.py`, `sample_data.py`, `requirements.txt`, `README.md`); keine weiteren
Quellmodule oder AGENTS.md vorhanden. Ausgangscommit:
`cc09088b0b0743e689f038b8ff9e696b42b0f27b`.

Befunde und Korrekturen:

* Bruttoverkauf ohne Abzug Verkaufs-USt. führte zu zu hohem Deckungsbeitrag und
  Maximalgebot: explizite Verkaufsbesteuerung und Brutto-/Netto-Trennung.
* Vorsteuer pauschal standardmäßig abziehbar: sichere Vorgabe aus, Berechtigung
  und Rechnungspositionen getrennt; Zahlungsbedarf immer inklusive Einkaufs-USt.
* Nebenkosten ohne eindeutige Steuerbasis: brutto und expliziter Vorsteuerbetrag.
* Differenzbesteuerung nicht abgebildet: sichtbar gesperrter Fall, keine erfundene
  steuerliche Einkaufspreisdefinition.
* Ungeprüfte Gebühren echter Plattformen: entfernt, rein fiktive Szenarien.
* Breite Tabelle und versteckte Sidebar: schmale Karten und sichtbare Einstellungen.
* Keine Tests, README oder Quellenarchitektur: ergänzt; ungenutzte Abhängigkeiten entfernt.

## Ausgeführt

Python 3.12.14, Streamlit 1.65.0, pytest 8.4.2.

* `python -m pytest -q`: **28 passed**, 0,96 Sekunden.
* Fachliche Tests: Brutto-/Nettoerlös, Einkaufs- und Verkaufs-USt., vollständiger
  und teilweiser Vorsteuerabzug, Brutto-Nebenkosten, steuerfreies Szenario,
  Sicherheitsabschlag, Nullkosten/-erlös, unerreichbare Zielmarge, Maximalgebot
  als mathematische Zielmargengrenze, Score-Grenzen/Gewichte, ungültige Eingaben.
* Streamlit AppTest: Start, Regelbesteuerung, Differenzbesteuerungssperre,
  ungültige Vorsteuer, leere Live-Ansicht und manuelles Formular ohne Ausnahme.
* Datenquellentest: alle Demo-Lose markiert; Live-Modus ohne Demo-Fallback.
* `python -m compileall -q app.py scoring.py sources.py sample_data.py`: bestanden.
* `git diff --check`: bestanden.
* Lokaler Streamlit-Server `/_stcore/health`: `ok`.

## Restrisiken

Steuerliche Eignung der Szenarien nicht festgestellt. Kein Rechtsgutachten oder
verbindliche Gebührenprüfung. Differenzbesteuerung benötigt gesonderte fachliche
Freigabe und Implementierung. Verkaufspreise sind erfunden, keine Nachfrageprüfung.
Keine echte Quelle, Persistenz, Hintergrundabrufe oder Authentifizierung in der
App. Private Cloud-Zugriffsrechte und aktuelle Gratis-Konditionen vor Deployment
prüfen. Keine Cloud-Veröffentlichung oder echte Gebotsabgabe durchgeführt.

## Mobile Browserprüfung

Playwright/Chromium gegen den lokalen Streamlit-Server, Touch-/Mobile-Kontext:
390 × 844 und 320 × 568 Pixel. Dokumentbreite jeweils gleich Viewportbreite,
kein horizontaler Überlauf. Screenshot geprüft; ein zunächst verdeckter Titel
wurde durch ausreichenden oberen Abstand korrigiert (Titeloberkante danach
96 px). Abschließender Testlauf: **28 passed**, 0,98 Sekunden. Chromium ersetzt
keinen Test auf einem echten iPhone mit Safari; dieser steht vor Veröffentlichung aus.
