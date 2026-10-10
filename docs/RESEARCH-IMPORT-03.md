# Rechercheimport und Praxisvalidierung 03

Die angekündigte `moebel_auktionen_20_recherche.csv` liegt in den bereitgestellten Anhängen nicht vor. Der DOCX-Beschaffungsatlas enthält Quellenbeschreibungen, keine 20 Angebotsdatensätze. Es wurde kein erfolgreicher Echtdatenimport behauptet. Das tatsächliche CSV-Schema ist unbekannt.

## Vorgeschlagenes Adapterformat

`research_import.parse_research_csv(bytes, mapping=None, delimiter=';', now=None)` verarbeitet einen nutzereigenen UTF-8-CSV-Export ohne Netzabruf. Der bisherige v1-Import bleibt unverändert. Die neue Vorlage ist ein Vorschlag, keine behauptete Anbieter-Schnittstelle.

Pflichtspalten: `source`, `source_id`, `title`, `listing_url`, `observed_at`, `rights_reference`. `currency` muss ausdrücklich `EUR` enthalten. `observed_at` bezeichnet den tatsächlichen Beobachtungszeitpunkt mit Zeitzone; Importzeit wird niemals dafür erfunden. `rights_reference` dokumentiert vom Nutzer bestätigte Nutzungsrechte; das Programm verifiziert diese Erklärung nicht rechtlich.

Optional: `location`, `ends_at`, `status` (`active`, `ended`, `unknown`), `price`, `price_kind`, `bid_basis` (`net`, `gross`, `unknown`), `description`, `terms_reference`. Spaltenzuordnung kann explizit als Dictionary kanonischer Name → tatsächlicher CSV-Name angegeben werden. Zusätzliche Originalspalten bleiben im Provenienz-Sidecar erhalten.

Preise: `current`, `starting`, `minimum`, `manual`, `hammer`, `total`, `unknown`. Zuschlags- und Gesamtpreise werden ausschließlich als Originalpreis gespeichert, niemals als aktuelles Gebot umgedeutet. Fehlende Preisarten bleiben ungeklärt. Dezimalpunkt oder Dezimalkomma werden akzeptiert; keine geratenen Tausendertrennzeichen oder Währungsumrechnung. Start-/Mindestpreise tragen ihre Preisart und bleiben durch die Bewertungssperre ausgeschlossen. Alle nicht gelieferten Finanzfelder bleiben `unknown`, Gebührenmodell immer ungeklärt.

Der Adapter liefert `ResearchBatch.listings`, `.duplicates` und `.provenance`. Provenienz enthält jede Originalzeile, ursprüngliche Preisart, Beschreibung, Zuordnung und fehlende Finanzfelder. Sie wird bei ausdrücklichem dauerhaftem Import atomar mit dem Listing gespeichert (Schema v2), separat exportiert und bei Sicherung/Wiederherstellung erhalten. Identische Quellenkennungen werden nach v1-Regeln wiederholbar verarbeitet; gleicher Zeitpunkt mit widersprüchlichen Werten sperrt den gesamten Import.

## Ableitungen

`intelligence.analyze_listing` erzeugt separate, deterministische Ableitungen mit Textbelegen und Zeichenpositionen. Kategorie, bekannte Marken, Material, Schäden und Zustandswörter beruhen auf wörtlichen Treffern. Stückzahl wird nur aus eindeutigen expliziten Stück/Stk-Angaben abgeleitet. Modelle bleiben unbekannt. Negationen und Kontext können Fehlklassifikationen erzeugen; deshalb keine bestätigten Produktmerkmale oder Kaufempfehlungen. Originaldaten werden nie überschrieben. Plattformübergreifend gleiche normalisierte Titel und Standorte erzeugen nur Prüfkandidaten, keine Zusammenführung oder Löschung.

## Praxistest

`validation_metrics.practice_metrics` benötigt eindeutige verarbeitete Listings und gemessene Zähler/Zeiten. Synthetische Tests sind ausdrücklich `synthetic`. Vollständige Finanzfelder bedeuten keine bestätigte Rentabilität. Zeitersparnis wird nur bei explizit gemessener manueller Zeit und Baseline berechnet. Kaufkandidaten, manuelle Verifikation und profitable Käufe bleiben ohne Nachweise unbekannt.

Nächster Praxistest: autorisierten Export von mindestens 20 echten Möbelangeboten bereitstellen; Quellenkennung und historische/aktive Einordnung manuell prüfen; Import und Wiederholungsimport messen; vollständige Datensätze und Sperrgründe auswerten; manuelle Recherchezeit derselben Angebote messen. Weiterentwicklung erst wirtschaftlich begründen, wenn mehrere manuell bestätigte Einkaufskandidaten entstehen. Keine Profitabilität ohne belegte reale Verkäufe. Bei dauerhaft fehlenden Rechten oder keiner messbaren Recherchezeitersparnis zuerst Zugang/Workflow ändern, statt weitere automatische Quellen zu bauen.

Auf dem iPhone: CSV im Dateien-Bereich speichern, im privaten Scanner den Rechercheimport wählen, das vorgeschlagene Spaltenformat verwenden und Importstatus prüfen (abweichende Zuordnungen sind derzeit nur über die Python-Schnittstelle möglich). Vor einer Kaufentscheidung Quelle, Losbedingungen, Steuerbasis und vollständige Kosten manuell bestätigen. Ohne eingerichtetes privates Hosting läuft der Scanner nicht dauerhaft auf dem iPhone.
