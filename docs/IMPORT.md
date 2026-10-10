# Datenvertrag v1 und Nutzerimport

Zwei Eingangsformate, ein Modell: `Listing` in `listings.py`. JSON hat genau
`schema_version: 1` und `listings: [ ... ]`. CSV ist UTF-8 (BOM erlaubt),
**Semikolon-getrennt**, mit dem exakten Kopf aus
[import-template.csv](../examples/import-template.csv). Dezimalpunkt oder -komma
im CSV-Zahlenfeld, keine Tausendertrennzeichen. JSON-Zahlen mit Dezimalpunkt.

## Angebot

| Feld | Bedeutung / Validierung |
|---|---|
| `source`, `source_id` | Stabile Quellkennung und originales Loskennzeichen; 1–100 Zeichen aus A–Z/a–z/0–9/._-. Dublettenschlüssel ist das Paar, nie nur die Losnummer. Enthält ein Originalzeichen andere Zeichen, muss ein späterer Adapter eine dokumentierte stabile Abbildung vorsehen. |
| `title`, `location` | Beobachteter Titel und Standort, jeweils maximal 300 Zeichen. Fehlenden Standort ausdrücklich z. B. `ungeklärt` schreiben; fehlende Details zusätzlich prüfen. |
| `listing_url` | Original-HTTPS-Adresse ohne eingebettete Zugangsdaten, lokalen Host oder Fragment. Nur Link, wird vom Scanner nicht abgerufen. |
| `observed_at` | Tatsächlicher Beobachtungszeitpunkt, ISO-8601 mit Zeitzone; **nicht** Importzeit einsetzen. Wird nach UTC normalisiert. Maximal 5 Minuten Zukunftstoleranz. |
| `ends_at` | Beobachtetes Ende mit Zeitzone oder JSON `null` / CSV leer. Keine erfundene Frist. |
| `status` | `active`, `ended`, `unknown`; keine Aktualisierung allein durch Import. |
| `currency` | Derzeit ausschließlich `EUR`; andere Währungen werden abgewiesen. |
| `bid_basis` | `net`, `gross`, `unknown`. Nur `net` wird kalkuliert. |
| `bid_kind` | `current`, `starting`, `minimum`, `manual`, `unknown`. Start-/Mindestpreis ist kein aktuelles Höchstgebot. `manual` erlaubt einen ausdrücklich selbst gewählten Plan-Zuschlag, z. B. bei verdeckter Ausschreibung. |
| `fee_model` | `net_hammer_plus_net_premium`, `other`, `unknown`. Nur das erste Modell wird gerechnet: Waren-USt. auf Netto-Zuschlag, Aufgeld-USt. auf Netto-Aufgeld. Mindest-/Staffelgebühren oder andere Basen bleiben gesperrt. |
| `terms_reference` | Beleg der konkret geprüften Auktionskonditionen (Dokument-/URL-/Versionsangabe). Nicht als pauschale Betreiberregel deuten. |
| `rights_reference` | Nachweis/Referenz der Rechte zum internen Datenimport, z. B. schriftliche Genehmigung mit Datum und Aktenzeichen. Die App prüft deren Inhalt nicht juristisch. Keine Zugangsdaten eintragen. |
| `fields` (JSON) | Alle neun Finanzfelder, jedes mit `value`, `origin`, `reference`. Im CSV als drei Spalten je Feld. |

Finanzfelder: `current_bid`, `expected_resale_gross`, `buyer_premium`, `item_vat`,
`premium_vat`, `transport`, `refurbishment`, `storage`, `disposal`.
Preise in EUR; Neben- und Verkaufskosten **brutto**, Gebotsbetrag entsprechend
`bid_basis`. Raten als Anteil (`0.18` = 18 %, nicht `18`). Zahlen endlich und
nicht negativ; operative Obergrenze 1 Milliarde, Raten maximal 1. Jede Null ist
eine explizite Aussage, kein Ersatz für fehlende Daten.

Herkunft (`origin`):

* `observed`: aus Originalangebot/Beleg entnommen; `reference` nennt den Beleg.
* `estimated`: Schätzung, z. B. Wiederverkauf oder Transport. Begründung und
  Schätzdatum in `reference` dokumentieren; keine gesicherte Marktpreisbehauptung.
* `manual`: bewusst geprüfte manuelle Eingabe; Beleg/Entscheidung dokumentieren.
* `unknown`: `value: null` (CSV leer), `reference` nennt die offene Frage.

Beispiel für einen **ungeklärten** Teil eines JSON-Angebots:

```json
"transport": {"value": null, "origin": "unknown", "reference": "Transportangebot fehlt"}
```

Keine vorbefüllten „echten“ Angebote im Repository. Test-Fixtures sind vollständig
fiktiv. Berechtigter Nutzerexport muss auf diesen Vertrag abgebildet werden;
PDF, HTML und beliebige Anbieter-Exceldateien werden nicht automatisch interpretiert.

## Verarbeitung und Empfehlungen

Maximal 2 MiB / 1.000 Lose pro Datei. Eine ungültige Zeile verwirft die gesamte
Datei. Doppelte JSON-Schlüssel, NaN/Infinity, unzulässige URLs, fehlende Spalten
und unbekannte Felder werden kontrolliert abgewiesen. Gleiche Quelle/Los-ID:
neuester Beobachtungsstand gewinnt; bei gleichem Zeitpunkt und widersprüchlichem
Inhalt wird die Datei verworfen. Quellenübergreifende Dubletten werden nicht
behauptet; sie benötigen künftig gemeinsame originale Asset-/Loskennzeichen.

Kalkulation nur nach manueller Prüfung, aktiver Auktion mit zukünftigem Ende,
Beobachtung maximal 24 Stunden alt, unterstützter Netto-/Gebührenbasis und
vollständigen Werten. Gebühren, Einkaufs-USt. und Gebot müssen beobachtet oder
manuell geprüft sein; Schätzungen dieser Werte sperren die Kalkulation.
24 Stunden ist eine **interne Qualitätsgrenze**, kein Anbieterlimit und keine
Aktualitätsgarantie; bei schnellen Auktionen vor jeder Entscheidung erneut prüfen.
Verkaufsbesteuerung bleibt explizit; Differenzbesteuerung weiterhin gesperrt.
Auch ein vollständiges Szenario ist keine autonome Kaufempfehlung.

Importierte Nebenkosten sind losbezogen; die allgemeinen Demo-Nebenkosten aus der
UI ersetzen sie nicht. Zielmarge, Abschlag und Verkaufs-/Vorsteuerszenario kommen
weiterhin aus expliziten UI-Eingaben. Vorsteuer auf Nebenkosten darf deren
Bruttosumme nicht überschreiten. Unbekannte Felder werden nicht aus der Demo ergänzt.

## Automatischer Datei-Scanner

Nur für einen autorisierten privaten Server/Entwicklungsraum, kein neues Hosting:

```sh
umask 077
mkdir -p inbox
python scanner.py --inbox inbox --database scanner.sqlite3 --workspace internal
# Wiederholte Verarbeitung im Vordergrund; keine Netzwerkabrufe:
python scanner.py --inbox inbox --database scanner.sqlite3 --workspace internal --watch --interval 60
# Privates Dashboard liest denselben Speicher:
SCANNER_ACCESS_MODE=private SCANNER_DATABASE=scanner.sqlite3 SCANNER_WORKSPACE=internal streamlit run app.py
```

Dateien erst komplett schreiben und dann atomar als `.csv`/`.json` in die Inbox
verschieben. Scanner verändert/löscht Eingabedateien nicht. Maximal 100 Dateien
pro Inbox; verarbeitete Dateien bei Bedarf privat archivieren. Reguläre Dateien,
keine Symlinks. SHA-256 pro Workspace verhindert wiederholtes Importieren derselben
Datei. SQLite-Transaktion pro Datei; ältere Stände überschreiben keine neueren.
Bei Fehlern der Einzeldatei laufen andere Dateien weiter. Einmaliger Lauf:
Exit 0 erfolgreich, 1 mindestens eine fehlerhafte Datei, 2 Konfiguration/Startfehler.
Watch-Modus wartet mindestens 60 Sekunden zwischen Durchläufen, stoppt mit Ctrl-C
und benötigt einen laufenden Serverprozess. Fehler werden bei späteren Läufen
erneut geprüft; kein externer Retry-/Rate-Limit-Code, solange kein Live-Adapter existiert.

UI-Uploads bleiben sitzungsgebunden und werden nicht automatisch in die Datenbank
geschrieben. Der Worker speichert dauerhaft auf seinem Dateisystem; keine
Cloud-Persistenz garantiert. Neue Datenbankdateien erhalten 0600; bestehende
Dateien, Backups, Journale und Verzeichnisse müssen serverseitig ebenfalls privat
geschützt werden. JSON-Logs nennen Dateinamen/Ergebnis, keine Angebotsinhalte.
