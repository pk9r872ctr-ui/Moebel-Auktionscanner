# Möbel-Auktionsscanner · interne Auction Intelligence

Mobile Streamlit-App, steuerbewusste Szenariokalkulation und automatischer
Datei-Scanner. **Kein freigegebener Live-Abruf**: Quellenrechte/Zugang sind noch
nicht nachgewiesen. Dafür ist ein getesteter Import echter, rechtmäßig vom
Nutzer bereitgestellter JSON-/CSV-Daten implementiert. Demo bleibt getrennt.
Keine Gebotsabgabe, kein Kauf, keine ERP-Änderung, kein Deployment.

## P1: privater Betrieb und Sicherungen

[Speicherstatus, verschlüsseltes Backup/Restore, iPhone-Abnahme und Grenzen](docs/P1-OPERATIONS.md).
Keine zugesicherte Neustart-/Redeploy-Persistenz auf Streamlit Community Cloud.
Backups werden vom Eigentümer heruntergeladen und privat aufbewahrt.

## P0-Echtdatenimport vorbereiten

[Importweg, Evidenzvertrag, Tests und offene Abnahme](docs/P0-IMPORT-ACCEPTANCE.md).
20 echte Recherchezeilen einschließlich Evidenzregister wurden technisch bis
ins Dashboard verarbeitet und bleiben gesperrt. Für keine Zeile liegt ein
ausreichender Rechtsbeleg vor: Die fachliche P0-Schwelle ist noch nicht erreicht.

## Auftrag 03: geprüfter Entwicklungsstand

21 Atlasquellen im versionierten Register, Rechercheadapter mit Originaldaten,
**182 bestandene Tests**, Beobachtungshistorie, Merkliste, Vollkosten-/Liquiditätsprüfung und versionierter
Kandidatenexport. **0 echte Angebote verarbeitet**: angekündigte Recherchedatei
fehlt, kein autorisierter Live-Katalogzugang nachgewiesen. 20 synthetische
Angebote technisch verarbeitet; kein belegter wirtschaftlicher Vorteil.

* [Vollständiger Entwicklungsbericht und Tests](docs/REPORT-03.md)
* [21 Quellen und Zugangsprüfung](docs/SOURCE-REGISTER-03.md)
* [Quellenregister JSON](data/source_registry.json)
* [Rechercheimport](docs/RESEARCH-IMPORT-03.md) · [Vollkostenmodell](docs/ECONOMICS-03.md)
* [Speicher, Sicherung und Betrieb](docs/STORAGE-03.md) · [Architektur und ERP-Vertrag](docs/ARCHITECTURE-03.md)
* [Einfache iPhone-Anleitung](docs/IPHONE-03.md)

## Grundlagen und verbleibende Grenzen

| Erreicht | Noch nicht erreicht |
|---|---|
| JSON/CSV-Validierung, Herkunft pro Finanzfeld, stabile Quellen-/Los-IDs | Live-Connector mit geprüfter Datennutzung |
| Dubletten, atomare SQLite-Imports, Wiederanlauf, automatischer Datei-Watch | Dauerhafter Cloud-Worker und automatischer Backupplan |
| Dashboard-Upload und Anzeige des Scanner-Speichers | Anbieter-Exports ohne manuelle Vertragsabbildung |
| Sperre bei fehlenden Daten, alten/abgelaufenen Angeboten oder Steuerfragen | Autonome Kaufempfehlung, Marktpreisvalidierung |
| Private OIDC-Sperre und Allowlist, PWA-Artefakte vorbereitet | Konfigurierter Identity-Provider, vollständige PWA-Installation |

* [Quellenvergleich und Primärbelege](docs/SOURCES.md)
* [Importvertrag, CSV und automatischer Datei-Scanner](docs/IMPORT.md)
* [Architektur, zukünftige API, ERP-Grenze und private PWA](docs/ARCHITECTURE.md)
* [Aktuelle Tests und Risiken](docs/VALIDATION-02.md)
* [Leere CSV-Vorlage](examples/import-template.csv)

## Entwicklung und Tests

Python 3.12:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
# Nur im privaten Entwicklungsraum; nicht öffentlich hosten:
SCANNER_ACCESS_MODE=local streamlit run app.py
```

Standardzugriff ist `private`: Ohne OIDC-Secrets und freigegebene Identität
stoppt die App. Es werden keine Passwörter in Git gespeichert.
`requirements.txt` enthält Streamlit mit Auth-Unterstützung. Versionsbereiche
sind kein Lockfile; Updates erneut testen. Finanzmodell aus PR #1 erhalten.

## Ausschließlich mit dem iPhone weiterarbeiten

1. In Safari den neuen Pull Request und „Files changed“ prüfen. Besonders
   `docs/SOURCES.md` und `docs/IMPORT.md` lesen. In „Checks“ Testresultate ansehen.
   Nicht ohne eigene ausdrückliche Freigabe mergen.
2. Quellenfreigabe bzw. einen rechtmäßig nutzbaren Export beschaffen. Für
   Zoll-/Justiz-Inhalte ist eine pauschale gewerbliche Weiterverwendung nicht
   belegt. Keine geschützten Inhalte einfach massenhaft kopieren. Der Scanner
   versendet keine Anfragen an Anbieter.
3. Berechtigten Export in iOS „Dateien“ speichern. Die leere CSV-Vorlage kann
   über GitHub in Safari heruntergeladen und z. B. in Numbers bearbeitet werden.
   Originale IDs, Beobachtungszeit, Währung und Belege eintragen; fehlende Zahlen
   leer und Herkunft `unknown` lassen. Export muss UTF-8 und **Semikolon** als
   Trenner haben; Format anhand des Importvertrags prüfen. Ein normaler
   Anbieterexport ist ohne Abbildung nicht automatisch kompatibel.
4. Keine echten Angebotsdateien, SQLite-Datenbanken oder Secrets ins Repository
   hochladen. Für Codeänderungen auf GitHub „Edit“ oder Codex nutzen; lokale
   Shellbefehle sind für einen späteren privaten Server, nicht für das iPhone.
5. **Derzeit gibt es keinen bereitgestellten App-Link.** Als nächstes nach
   Quellen-/Exportabnahme den privaten Hosting- und OIDC-Aufbau separat
   freigeben. Möglich ist eine private Streamlit-Cloud-Instanz mit geprüftem
   Gratisangebot; Kosten, Zugangsschutz und Persistenz vorab klären. Keine
   Karte oder kostenpflichtigen Dienste aktivieren. Für den dauerhaften
   Datei-Scanner genügt eine schlafende Gratis-Dashboard-Instanz nicht.
6. Sobald später ein freigegebener privater HTTPS-Link existiert: anmelden,
   „Echte Daten aus Nutzerimport“ wählen, Rechte bestätigen, Datei aus „Dateien“
   hochladen. Herkunft/Blockaden prüfen. Loskosten und Gebühren im Export
   korrigieren, erneut hochladen; erst dann Steuer- und Review-Szenario wählen.
   Importierte Nebenkosten kommen aus dem Los, nicht aus Demo-Vorgaben.
7. Safari → Teilen → „Zum Home-Bildschirm“ → gegebenenfalls „Als Web-App öffnen“.
   [Apple-Anleitung](https://support.apple.com/en-eg/guide/iphone/iphea86e5236/ios).
   Dies startet die private Web-App; es bewirkt keinen Offline- oder
   Hintergrundscan. Eine vollständige Manifest-Einbindung steht noch aus.

Kein Hosting im Auftrag aktiviert. Für spätere OIDC-Konfiguration und Manifest-
Einbindung siehe [Architektur](docs/ARCHITECTURE.md) und die
[offizielle Streamlit-Authentifizierung](https://docs.streamlit.io/develop/concepts/connections/authentication).
Echte Safari-/OIDC-Abnahme bleibt vor Inbetriebnahme erforderlich.

## Berechnung und Grenzen

Alle Werte in Euro. Kalkulationspläne bleiben im Sitzungszustand; importierte Angebote und Originalprovenienz können bei konfigurierter privater Datenbank ausdrücklich gespeichert werden. Der folgende Abschnitt beschreibt den Basisrechner; zusätzliche Kosten und Liquidität behandelt das verlinkte Vollkostenmodell.

* Zuschlag **netto**, Aufgeld als Prozentsatz des Netto-Zuschlags. Waren-USt. auf
  Zuschlag, Aufgeld-USt. nur auf Netto-Aufgeld. Das sind ausdrücklich gewählte
  Rechenbasen, keine behaupteten Gebührenregeln einer Plattform.
* Zahlungsbedarf = Zuschlag + Aufgeld + beide USt.-Beträge + Brutto-Nebenkosten.
  Wirtschaftliche Kosten = Zahlungsbedarf − bestätigte abziehbare Vorsteuer.
* Sicherer Bruttoerlös = geschätzter Brutto-Verkaufspreis × (1 − Abschlag).
  Regelbesteuerung: Verkaufs-USt. = Bruttoerlös × Satz / (1 + Satz).
  Erlös nach Verkaufs-USt. = Bruttoerlös − Verkaufs-USt.
* Vorsteuer standardmäßig **aus**. Berechtigung sowie Abzug von Waren- und
  Aufgeld-USt. separat bestätigen. Nebenkosten bleiben brutto; nur ein explizit
  bestätigter Vorsteuerbetrag wird abgezogen. Ein Satz von 0 % bedeutet nicht
  automatisch Privatverkauf, Kleinunternehmerstatus oder Differenzbesteuerung.
* Szenario ohne Verkaufs-USt. rechnet ohne Vorsteuerabzug. Seine rechtliche
  Anwendbarkeit muss außerhalb der App geklärt werden.
* **Ungeklärte Fälle und Differenzbesteuerung sind gesperrt**: keine Gewinn-,
  Maximalgebots- oder Score-Aussage. Für § 25a UStG sind unter anderem
  Berechtigung, Herkunft und steuerlicher Einkaufspreis zu klären. Die App setzt
  Aufgeld oder Transport nicht ungeprüft als steuerlichen Einkaufspreis an.
  Ein späteres Modul benötigt geprüfte Regeln und passende Rechnungsdaten.
* Deckungsbeitrag = Erlös nach Verkaufs-USt. − wirtschaftliche Kosten.
  Marge = Deckungsbeitrag / Erlös nach Verkaufs-USt.; ROI = Deckungsbeitrag /
  wirtschaftliche Kosten. Bei Nenner 0 wird 0 ausgegeben, keine unendliche Rendite.
* Maximaler Netto-Zuschlag = (Erlös × (1 − Zielmarge) − wirtschaftliche
  Nebenkosten) / Kostenfaktor des Zuschlags. Der Kostenfaktor enthält Aufgeld und
  nicht abziehbare Einkaufs-USt. Negative Ergebnisse werden 0; wenn selbst bei
  Zuschlag 0 die Zielmarge unerreichbar ist, zeigt die App eine Warnung.
  Unrunde Ergebnisse sind Planung, keine zulässigen Gebotsschritte.
* Deal-Score 0–100: 35 Punkte Marge (Sättigung bei 45 %), 25 ROI (100 %),
  20 Gebotsspielraum, 20 Deckungsbeitrag (5.000 €). Jeder Teil wird auf 0–1
  begrenzt. Dies ist eine dokumentierte Heuristik, keine Marktvalidierung.

Beispiel: Zuschlag 1.000 €, Aufgeld 20 %, beide Einkaufs-USt. 19 %, Nebenkosten
100 € brutto, Verkauf 2.380 € brutto ohne Abschlag: Zahlungsbedarf 1.528 €,
Verkaufs-USt. 380 €, Erlös 2.000 €, Deckungsbeitrag ohne Vorsteuer 472 €.

Nicht modelliert: abweichende Steuerbasen, Bruttopreis-Zuschläge, Mindest- oder
Staffelgebühren, gemischte Steuersätze, grenzüberschreitende Fälle, automatische Finanzierungsermittlung,
Arbeitszeitbewertung, Ertragsteuern und rechtliche Eignung eines
Steuermodus. Rundung erfolgt nur zur Anzeige; Rechnungssummen können durch
positionsweise Cent-Rundung abweichen. Vor Verwendung für echte Entscheidungen
Rechnungen, Auktionsbedingungen und steuerliche Behandlung prüfen lassen.
