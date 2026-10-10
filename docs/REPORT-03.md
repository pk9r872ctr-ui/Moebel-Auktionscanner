# Entwicklungs- und Validierungsbericht 03 · 10.10.2026

## Ausgangspunkt und Bestandsaufnahme

Basis `main` / `867e009` (PRs #1 und #2 übernommen), Branch `feat/auction-intelligence-engine`. Ausgangsprüfung: **96 Tests bestanden**. Vorhandene Python-Module, Importvertrag, SQLite-Speicher, Tests, Zugriffsschutz, Konfiguration, CI und Dokumentation wurden überprüft; Finanzkern und bestehender Importvertrag bleiben kompatibel. Kein ERP-Repository gelesen oder geändert.

Priorisierte Befunde:

| Priorität | Befund | Ergebnis |
|---|---|---|
| Kritisch | Truthy Textwerte konnten Vorsteuerberechtigung vortäuschen | Finanzkern verlangt echte boolesche Flags; Review-Text erteilt keine Freigabe |
| Kritisch | Entscheidung konnte bei parallelem Scan an ungesehenen neuen Stand gebunden werden | UI übergibt erwarteten Snapshot; atomarer Vergleich sperrt veraltete Anzeige |
| Hoch | Nur neuester Stand, keine überprüfbare Änderungshistorie | Migration auf SQLite-Schema v2, unveränderliche Beobachtungen, ältere Konflikte gesperrt |
| Hoch | Recherche-Originalfelder könnten beim Normalisieren verloren gehen | Provenienz atomar speichern, separat exportieren und sichern |
| Hoch | Fehlende zusätzliche Handelskosten und Liquidität | Expliziter Vollkostenplan; unbekannt sperrt Ergebnis |
| Hoch | Quelle, Gebühren und Zugriff ungeprüft als Plattformstandard | Versioniertes Register mit 21 Quellen, losbezogene Konditionen erforderlich |
| Mittel | Keine gespeicherten Entscheidungen, Laufberichte oder Backup-Prüfung | Merkliste, Kandidatenbindung, Scannerstatus, validierte Sicherung/Wiederherstellung |
| Mittel | Keine echten Daten/Marktpreise, kein laufender privater Host | Unverändert echte Abnahmeblockaden; keine Funktionsbehauptung dafür |

## A. Implementierte Funktionen

Strenger v1-CSV/JSON-Import bleibt erhalten. Neuer Recherche-CSV-Adapter mit expliziter Spaltenzuordnung als Python-API, Originalzeilen, Preisarten und unbekannten Feldern. Dashboard unterstützt vorgeschlagenes Rechercheformat, sitzungsgebundenen Upload und ausdrückliches dauerhaftes Speichern bei konfigurierter privater Datenbank. Originalbeschreibung wird für Merkmalsanalyse herangezogen, sofern sie zum selben Snapshot gehört.

Modulare, belegte Textableitungen für Kategorien, ausgewählte Marken, Material, Zustand, Schäden und ausdrücklich genannte Stückzahl. Modell bleibt unbekannt; weder Negationsauflösung noch umfassende Produktidentifikation. Mögliche plattformübergreifende Dubletten sind Hinweise, werden nicht gelöscht oder automatisch zusammengeführt.

Suche, Plattform-/Kategorie-/Standort-/Status-/Preis-/Endzeit-/Finanzvollständigkeitsfilter und Filter für manuelle Entscheidungen. Preisfilter normalisieren keine unterschiedlichen Preisbasen. Keine automatische Rangliste belastbar rentabler Angebote ohne Eingaben.

## B. Datenquellen

Alle **21 Atlasquellen** extrahiert und anhand verfügbarer öffentlicher offizieller Informationen recherchiert. Belege, Dokumentstände, Einschränkungen und getrennte Prioritäten stehen im [Quellenbericht](SOURCE-REGISTER-03.md) und [Register](../data/source_registry.json). Atlas-DOCX mit SHA256 referenziert, privates Original nicht veröffentlicht.

Keine Quelle besitzt hier einen nachgewiesenen kostenlosen autorisierten gewerblichen Katalogzugang. Alle Live-Connectoren gesperrt. Besonders Zoll/Justiz verlangen Nutzungsfreigaben; Justiz-Steuerbehauptung im Atlas ist widersprüchlich, AssetOrb-Identität nach Weiterleitung ungeklärt. Öffentlich sichtbare Website oder Partner-API beweist keine Scanberechtigung. Nicht erreichbare/alte/indirekte Belege ausdrücklich gekennzeichnet.

## C. Echtdaten und Praxistest

**0 echte Angebote erfolgreich verarbeitet.** Die Datei `moebel_auktionen_20_recherche.csv` fehlt sowohl im Workspace als auch in den bereitgestellten Anhängen. Der Atlas enthält keine Angebotsliste. Kein erfolgreiches Live-Scanning behauptet.

Technischer Test mit **20 synthetischen Angeboten**: 20 eingefügt, wiederholter Digest vollständig übersprungen, 20 nach Backup/Restore erhalten, Originalzeilen erhalten, 0 Importfehler. Gesamtdauer einschließlich Adapter, Speicherung, Wiederholung und Backup/Restore ca. **0,042 Sekunden** auf dieser Umgebung; kein Produktionsbenchmark. Alle 20 wirtschaftlich gesperrt, da absichtlich notwendige Angaben fehlen. Reproduzierbar mit `python scripts/synthetic_practice.py`; Ergebniszeiten sind umgebungsabhängig. Vollständige Messdaten: [PRACTICE-03.json](PRACTICE-03.json). Wiederholungsverarbeitung und Dublettenerkennung zusätzlich durch automatisierte Tests geprüft.

Kein manueller Zeitvergleich erhoben, keine Einsparung, keine interessanten echten Einkaufskandidaten und keine realisierten Gewinne nachgewiesen. Diese Werte bleiben unbekannt.

## D. Wirtschaftlichkeit

[Vollkostenmodell](ECONOMICS-03.md): Gebot, netto-prozentuales Aufgeld und getrennte Waren-/Aufgeld-USt.; bestätigte Vorsteuer; Transport, Aufbereitung, Lager, Entsorgung; zusätzliche Abholung, Demontage, Verladung, Verkaufs-/Fixgebühren und Finanzierung. Konservative Verkaufsspanne, Ausschuss, Sicherheitsabschlag, Zielmarge, Zieldeckungsbeitrag und Bruttoliquidität begrenzen Szenario und Maximalgebot.

Einkaufsmodi Regelbesteuerung / keine USt ausgewiesen / ausdrücklich differenzbesteuert / ungeklärt getrennt vom Verkauf. Keine implizite §25a-Berechtigung. Differenzbesteuerung beim Verkauf bleibt gesperrt. Fehlende Planfelder einschließlich Nullkosten verlangen ausdrückliche Eingaben. Heuristischer wirtschaftlicher Score ist keine Marktpreis- oder Gewinnerwartungsvalidierung; technische Vollständigkeit wird separat angezeigt. Verkaufsdauer ist dokumentiert, Finanzierung explizit geplant; kein frei erfundener Zeit-/Attraktivitätsbonus.

Keine unterstützte Berechnung für Brutto-Zuschlag, Mindest-/Staffelaufgeld, andere Steuerbasen, gemischte Steuersätze oder grenzüberschreitende Fälle. Arbeitszeit muss als entsprechende zusätzliche Kosten geplant werden; Ertragsteuern und Rechnungs-Centrundung sind nicht modelliert. Basisrechner/Demo weiterhin bewusst eingeschränkte Szenarien, keine vollständige Kaufempfehlung.

## E. Automatisierung

Datei-Scanner verarbeitet berechtigte v1-Dateien wiederholt ohne manuelles Eingreifen, mit Digest-Idempotenz, Transaktion, isolierten Fehlern und gespeicherten Laufberichten. Kein Website-Abruf. Rechercheadapter derzeit Dashboard/Python-API, nicht automatisch im v1-Datei-Worker erkannt.

Watch-Modus braucht dauerhaft laufenden privaten Rechner/Server, persistenten Datenträger und Betrieb/Überwachung. iPhone und schlafendes Gratis-Dashboard ersetzen keinen 24/7-Worker. Zeitsteuerung kann den bestehenden einmaligen CLI-Lauf auf einem später freigegebenen Server starten; kein Schedulerdienst aktiviert. Sicherung/Wiederherstellung verfügbar, aber kein automatischer Sicherungsplan oder getesteter Serverausfallbetrieb. [Betrieb](STORAGE-03.md).

## F. Sicherheit

Default private: vor Datenanzeige ohne passende OIDC-Konfiguration gesperrt, Allowlist nach issuer/subject; lokaler Entwicklungsmodus ausdrücklich nötig. Automatisiert fehlende Konfiguration, falsche Identität, Login-Grenze und Allowlist geprüft. Kein echter Provider-Roundtrip oder Penetrationstest. Keine neuen Secrets, Konten, bezahlten Dienste oder externen Nachrichten.

Workspace serverseitig konfiguriert, kein UI-Mandantenwechsel. SQLite-Dateineuanlage und neue Backups 0600; Pfad-/Symlinkprüfungen, exklusive Wiederherstellung, Importlimits und kontrollierte Speicherfehler. Keine Verschlüsselung oder SaaS-Autorisierung behauptet. Originaldaten/Exporte bleiben privat; Datenbank/Backups nicht in Git. Historientrigger verhindern normale Updates, nicht administrative Manipulation. Abhängigkeiten sind Versionsbereiche ohne Lockfile; `pip check` prüft Kompatibilität, keine CVE-Freiheit.

## G. Mobile Anwendung

Karten, sichtbare Filter, Losdetails, Vollkostenformular, Merkliste, Entscheidungen, Quellenlinks und Import-/Scannerstatus. Chromium/Playwright: **390×844 und 320×568**, Recherche-CSV-Upload sichtbar, Vollkostenformular öffnet, Dokumentbreite gleich Viewport, keine JS-Fehler. Screenshot geprüft. Keine echten Safari-/iPhone-, Offline-, Push- oder Hintergrundtests.

Manifest/Icon bleiben Hosting-Vorbereitung, nicht vollständig eingebundene installierbare PWA. Kein privater HTTPS-Link eingerichtet, kein Deployment. Vor Installation benötigt es erlaubtes privates Hosting, OIDC/TLS-Abnahme und Manifest-/Scope-Einbindung. [iPhone-Anleitung](IPHONE-03.md).

## H. ERP

`contracts.py` erzeugt/validiert versionierten `opportunity.selected`-Export mit stabiler Quellen-/Loskennung, vollständigem Snapshot, Freigabestatus und Snapshotzeit. Nur manuell ausgewählte aktuelle Kandidaten, ausdrücklich kein Rentabilitätsnachweis. Updates invalidieren Kandidatenexport. Keine Übermittlung, HTTP-Endpunkte, Buchhaltung, Lager-/Artikelverwaltung oder Annahmen über unbekanntes ERP-Datenmodell. [Architektur](ARCHITECTURE-03.md).

## I. Tests

Python 3.12.14, Streamlit 1.65.0, pytest 8.4.2. **182 Tests bestanden, 0 fehlgeschlagen** (`python -m pytest -q`, 3,91 Sekunden). `pip check`, `compileall` und `git diff --check` bestanden. CI im Pull Request separat prüfen. Prüfungen umfassen bisherigen v1-Import und Finanzkern, Research-Preissemanik, Originaldaten, Textbelege, Dublettenhinweise, Filter/Metriken, Steuer-Gates, Kosten-/Gebotsgrenzen, SQLite-Migration, Konfliktrollback, Beobachtungshistorie, Workspace, Entscheidungen, Scanstatus, Backup/Restore und Kandidatenvertrag. Zusätzlich Streamlit AppTest Merkliste/Filter und mobiler Browserupload.

Nicht ausgeführt: echte Quelle/Echtdatenabnahme, 20 reale Praxisangebote, reale Verkaufsdaten, Quellenautorisierung, OIDC-Provider, echter Safari/iPhone, Last-/Mehrkunden-/24h-Betrieb, vollständiger Securityaudit. Grüne Unit-Tests ersetzen diese Prüfungen nicht.

## J. Blockaden und technische Schulden

Rechte und tatsächlicher autorisierter Export fehlen. Keine Preisvergleichsdaten und kein bestätigtes Steuer-/Gebührenprofil pro Los. Private Bereitstellung/Identität/Persistenz ungeprüft. SQLite-Historie/Scanläufe wachsen ohne Retention; Speicher und Backups müssen betrieben werden. Keine gespeicherten Vollkostenpläne oder Bewertungsrevisionen: diese UI-Eingaben bleiben in der Sitzung. Kandidatenexport ist Auswahl-/Snapshotvertrag, kein vollständiger Kalkulationsexport. Kategorielexikon begrenzt, mögliche Dubletten quadratisch; Lastgrenzen später messen. Keine betriebsfähige SaaS, umfassende Marktbewertung oder autonome Einkaufsentscheidung.

## K. Nächste Entwicklung und Stoppkriterien

Höchster Nutzen: **rechtmäßig nutzbaren Export mit mindestens 20 echten Möbelangeboten bereitstellen**, tatsächliches Format abbilden und IDs/Preisarten/Status manuell verifizieren. Dann denselben Workflow messen: vollständige Werte, Sperrgründe, Dubletten, Fehler, Bearbeitungszeit und manuelle Baseline. Für wirtschaftliche Kandidaten Kosten/Steuern/Verkaufsspanne mit Belegen vervollständigen. Erst bei mehreren manuell bestätigten Kandidaten und messbarer Zeitersparnis einen autorisierten Connector und privaten dauerhaften Betrieb priorisieren.

Bei fehlenden Rechten bleibt Quelle gesperrt; bei dauerhafter Unbewertbarkeit zuerst fehlende Daten statt weitere Connectoren lösen. Wenn kein Beschaffungsvorteil messbar wird, Zugang/Workflow ändern und nicht SaaS-Infrastruktur ausbauen. Gewinn erst anhand realer Kauf-/Verkaufsbelege beurteilen. Kein Merge ohne ausdrückliche Freigabe.
