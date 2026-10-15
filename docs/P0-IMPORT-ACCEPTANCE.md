# P0: Importvorbereitung und Abnahme

## Stand und Blockade

Basis `main` / `7fabc47` im Repository `v7nc35/Moebel-Auktionscanner`:
200 bestehende Tests bestanden. Bestehende Module `research_import.py`,
`scanner.py` und `app.py` gezielt erweitert. Kein neues Speicherschema,
keine Versions-, Auth-, Finanzkern- oder ERP-Vertragsänderung.

**20 echte, vom Nutzer bereitgestellte Recherchezeilen technisch verarbeitet;
0 nachweislich zur geschäftlichen Inhaltsnutzung freigegebene Angebote.**
Beide Dateien liegen jetzt vor und wurden tatsächlich eingelesen. Das
P0-Evidenzregister enthält bei allen 20 Referenzen
`P0_BLOCKED_PROVENANCE_RIGHTS` / `purchase_recommendation=blocked`.
`rights_reference`, `original_observed_at` und `original_price_evidence` sind
jeweils leer. Die Schwelle von mindestens zehn rechtmäßig belegten Angeboten
ist **nicht erreicht**. Es wurde kein Ersatzbeleg erzeugt und keine Quelle
abgerufen. Der Import dient ausschließlich der privaten technischen Prüfung
als gesperrter Recherchehinweis, nicht einer bestätigten gewerblichen Nutzung.

Tatsächlicher Lauf (15.10.2026): 20 eingefügt, 0 Dubletten in der Datei,
Wiederholungsimport übersprungen, 20 Original-/Registerzeilen mit separater
Nutzerbestätigung erhalten. SQLite-Speicherung und Backup/Restore stimmen
vollständig überein. Alle 20 Finanzbewertungen gesperrt, alle Finanzwerte
`unknown`, 0 Kaufkandidaten. 17 ursprüngliche beendete Lose bleiben `ended`,
die zwei ursprünglich offenen und das abgebrochene bleiben `unknown` und
werden nicht als aktive Kaufangebote behandelt.

Streamlit-AppTest hat 20 gesperrte Karten aus dem tatsächlich befüllten Speicher
angezeigt. Dafür wurde der bestehende private Gate mit einer ausschließlich
synthetischen autorisierten Testidentität geprüft; kein realer Google-Login.
Dauer inklusive Import, Wiederholung, Restore und Dashboard ca, 1,25 Sekunden
in dieser Umgebung, kein Produktionsbenchmark. Aggregate mit SHA256 der
beiden Originaldateien: [P0-RESULTS.json](P0-RESULTS.json). Rohdateien und
Datenbank bleiben außerhalb des öffentlichen Repositorys. Die lokale
Prüfdatenbank liegt unter `/workspace/p0-private-validation/scanner-final.sqlite3`;
kein dauerhafter Cloudbetrieb oder Zugriff vom iPhone eingerichtet.


## Import ohne neue Architektur

Im privaten Dashboard „Echte Daten aus Nutzerimport“ → Importvertrag
„P0: historische deutsche Recherche-CSV“. Die bekannten neun deutschen
Originalspalten werden streng geprüft:

`quelle;auktions_id;titel;standort;angezeigter_betrag_eur;auktionsende_datum;status_am_2026_10_10;original_url;datenhinweis`

Nur die vorliegende Zoll-Rechercheform wird unterstützt, keine erfundenen
Anbieterformate. Quelle, Original-URL und Kennung müssen zusammenpassen.
Maximal 2 MiB/1.000 Zeilen. Ungültige oder widersprüchliche Originalzeilen
verwerfen den gesamten Import. Identische Wiederholungen werden erkannt.
Keine Netzwerkabfrage findet statt.

V1-Listings dienen als **gesperrte Recherchehinweise**. Das vorhandene
`import_provenance`-Sidecar speichert Originalzeile, ursprünglichen Betrag,
ursprüngliche Hinweise, Original-Enddatum und Statuskontext getrennt von der
Nutzerbestätigung aus V04. Erst bei explizit übergebener Bestätigung heißt die
Preisart dort `hammer`; andernfalls `unknown`. Das ist kein aktuelles Gebot,
Gesamtkaufpreis oder unabhängiger Zuschlagsnachweis. Alle Finanzfelder des
Listings bleiben `unknown`, einschließlich `current_bid`.

`Listing.observed_at` ist für diesen Adapter immer der technische Empfang des
Rechercheimports (`observed_at_kind=import_receipt_only`), keine erfundene
Quellenbeobachtung. Eine belegte Quellenzeit wird separat als
`source_observed_at` erhalten; ohne Beleg bleibt sie `null`. Das Datum im
Original-Spaltennamen ist nur `original_status_as_of`, kein bewiesener Abruf.
Ein Enddatum ohne Uhrzeit wird nicht auf Mitternacht geraten (`ends_at=null`).
Originalstatus `beendet` ergibt `ended`; andere historische Angaben bleiben
`unknown`, niemals automatisch `active`.

Speichern geschieht ausdrücklich in der bereits konfigurierten privaten
SQLite-Datenbank. Keine Datenbank konfiguriert: nur Sitzungsvorschau. Der
Digest umfasst CSV, Evidenzdatei und Bestätigung. Derselbe Import wird
übersprungen; geänderte Belege/Bestätigungen sind neue Importereignisse.
Vorhandene Beobachtungen und ursprüngliche Provenienz bleiben erhalten.
Kollidiert ein P0-Hinweis mit einer bereits regulär erfassten Quellen-/Los-ID,
wird der Import atomar zur manuellen Prüfung abgewiesen; der technische
Empfang darf das reguläre Angebot nicht als vermeintlich neue Beobachtung überschreiben.
Ein neuer technischer Empfang verhindert, dass ältere nachgereichte
Quellenzeiten die neuesten Prüfeinträge unbemerkt verdrängen.

## Tatsächliches CSV-Register und ergänzendes JSON-Format

Die bereitgestellte Datei `Moebelscanner_P0_Evidenzregister_20_Referenzen.csv`
wird mit ihrem tatsächlichen Format unterstützt: die neun Originalspalten plus
`source_id_normalized`, `price_kind_user_claim`, `price_kind_original_evidence`,
`original_observed_at`, `rights_reference`, `original_price_evidence`,
`data_status`, `purchase_recommendation`. Jede kopierte Originalzelle und Kennung
muss mit der CSV übereinstimmen. Abweichungen, doppelte Kennungen oder unbekannte
Spalten werden kontrolliert abgewiesen. Das unveränderte Register wird je Zeile
unter `original_evidence_row` erhalten.

Dieses Registerformat deklariert blockierte Referenzen, enthält aber keine
vollständige Freigabeprüfung mit Nutzungsumfang, Prüfer und Prüfzeitpunkt.
Es wird daher niemals allein aus einem eingetragenen Link eine kommerzielle
Nutzungsfreigabe abgeleitet. Auch eine später eingetragene Beobachtungszeit
bleibt als unbelegte Originalangabe erhalten, bis ihr Zeitbeleg vorliegt.
Unerwartete Freigabestatus benötigen eine neue explizite Vertragsabbildung.

Zusätzlich ist der folgende ausdrücklich **vorgeschlagene JSON-Vertrag** für
spätere dokumentierte Prüfungen vorbereitet; er ist nicht das Format der
bereitgestellten CSV-Datei.

[Leere Vorlage](../examples/p0-evidence-template.json): Schema1, SHA256 der
vollständigen CSV und `entries`. Die UI erzeugt nach Upload eine leere Vorlage
mit passendem CSV-Fingerprint. Einträge haben exakt folgende Felder; unbekannte
Belege bleiben `null`:

```json
{
  "source": "zoll-auktion",
  "source_id": "HIER_ORIGINALE_KENNUNG",
  "rights_status": "unknown",
  "rights_scope": null,
  "rights_reference": null,
  "reviewed_by": null,
  "reviewed_at": null,
  "source_observed_at": null,
  "time_reference": null,
  "hammer_verification": "unknown",
  "hammer_reference": null
}
```

`rights_status`: `unknown`, `restricted`, `documented`. Letzteres verlangt
`rights_scope=internal_commercial_import`, einen konkreten Rechtebeleg, Prüfer
und tatsächlichen Prüfzeitpunkt mit Zeitzone. Das ist eine deklarierte manuelle
Prüfung; der Parser garantiert nicht die materielle Gültigkeit einer Lizenz.
Öffentliche Abrufbarkeit, Nutzerbestätigung von Preisen und Import-Checkbox sind
keine kommerzielle Inhaltslizenz. Belege müssen den konkreten Datensatz und die
interne geschäftliche Nutzung abdecken.

`hammer_verification`: `unknown` oder `documented` mit separatem
`hammer_reference`. Eine reine Nutzerbestätigung ersetzt diesen unabhängigen
Beleg nicht. Quellenzeit benötigt `time_reference`. Zukunftszeiten,
Dublettenkennungen, fremde Quellen und falsche CSV-Fingerprints werden abgewiesen.
Alle Original-Evidenzfelder bleiben im Sidecar erhalten. Der Import lädt keine
Beleg-URLs oder lokalen Dokumente; Zugang und rechtliche Tragfähigkeit bleiben
manuell zu prüfen.

Auch ohne Register ist die private technische Vorschau/Speicherung als
ungeklärter Recherchehinweis möglich. Dies ist keine Bestätigung, dass Inhalte
rechtmäßig weiterverwendet werden dürfen. Solche Datensätze zählen nicht als
nachweislich zulässige P0-Angebote und erhalten keine Empfehlung.

## Gates, Oberfläche und Grenzen

Dashboard-Karten kennzeichnen fehlende Rechts-, Zeit- und Zuschlagsbelege sowie
unveränderte Originalhinweise sichtbar als prüfpflichtig. Finanz-/Steuergates
bleiben gesperrt, selbst bei vollständigen Rechtseinträgen, weil historische
Zuschläge keine aktuellen Kaufangebote sind. Keine Finanzdefaults aus Quellen.
P0-Datensätze können gemerkt oder verworfen, aber nicht als Einkaufskandidat
markiert werden. Speicher und Kandidatenexport sichern diese Grenze zusätzlich;
das vorhandene ERP-Exportformat bleibt unverändert.

Alle 21 Registerquellen bleiben erhalten. Explizite P0-Reihenfolge:
RESTLOS → Hämmerle → Proventura → NetBid → Zoll-Auktion. Dies aktiviert keinen
Connector und behauptet keine Zugriffsrechte.

## Reproduzierbare Abnahme

Python 3.12.14, Streamlit 1.65.0, pytest 8.4.2.
`python -m pytest -q`: **216 bestanden, 0 fehlgeschlagen**, 5,45 Sekunden.
Paketkompatibilität, Python-Kompilierung und `git diff --check` bestanden.
Diese automatisierten Tests verwenden synthetische Daten; der separate
oben dokumentierte Abnahmelauf verwendet die echten Anlagen.

Privater Wiederholungslauf ohne Netzwerk (keine vorhandenen Berichtsdateien
überschreiben; Pfade in einem privaten Verzeichnis außerhalb Git wählen):

```sh
python scripts/validate_p0_import.py --csv /private/moebel_auktionen_20_recherche.csv --evidence /private/Moebelscanner_P0_Evidenzregister_20_Referenzen.csv --database /private/p0.sqlite3 --confirmation-context "V04: Nutzer bestätigt Zuschlagspreise; unabhängig unbelegt" --report /private/acceptance.json
```


`python -m pytest -q` prüft bestehende Auth-, Import-, Finanz-, Speicher- und
ERP-Verträge plus P0. `tests/test_p0_import.py` prüft zehn synthetische Datensätze
von CSV über Validierung und SQLite bis zur tatsächlichen Streamlit-Ansicht:
Originalerhalt, separate Bestätigung, unbekannte Finanzwerte, gesperrte Gates,
Dubletten/Konflikte, Wiederholungsimport, Workspace-Speicherung, Backup/Restore,
Rechte-/Zeit-/Preiswarnungen, Quellenbestand und Kandidatensperre. Änderungen der
Evidenz bleiben in Importhistorie/Sidecars nachvollziehbar. Kein echter
Google-Login, iPhone/Safari-Test oder fachliches Lizenzgutachten durchgeführt.

Noch erforderliche Maßnahmen für die fachliche P0-Abnahme:

1. Vorliegende SHA256/Spalten beibehalten; konkrete fehlende Nutzungs-, Zeit- und Preisnachweise ergänzen.
2. Rechtsbelege je Kennung manuell beurteilen; mindestens zehn ausreichend
   belegte reale Angebote für den P0-Meilenstein zählen, unbekannte separat.
3. Privaten Import durchführen, gespeicherte Originale/Bestätigung vergleichen,
   Wiederholung und Dubletten zählen; keine fremden Dateien oder Belege erfinden.
4. Dashboardnachweis der gespeicherten Daten und Bewertungssperren erstellen;
   fehlende Zeiten und beendete Lose bleiben gesperrt.
5. Abnahmebericht mit echten Zählern, Belegreferenzen und verbleibenden Lücken
   ergänzen. Keine App-Veröffentlichung oder automatische Freigabe.
