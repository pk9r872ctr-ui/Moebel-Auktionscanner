# Möbel-Auktionsscanner · Planungs-MVP

Streamlit-Dashboard mit fiktiven Möbel-Losen und manueller Kalkulation. Auf dem
Cloud-Server läuft Python; am iPhone genügt Safari. Keine Live-Quelle, kein
Scraping, keine Gebotsabgabe. Es wurde kein Hosting aktiviert oder veröffentlicht.

## Start und Tests

Python 3.12 wird in CI getestet.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
streamlit run app.py
```

Für Hosting genügt `requirements.txt`. Die Abhängigkeiten sind auf Hauptversionen
begrenzt, aber kein reproduzierbarer Lockfile; Updates erneut testen. Unbenutzte
Direktabhängigkeiten pandas, requests und BeautifulSoup wurden entfernt.

## Berechnung und Grenzen

Alle Werte in Euro. Eingaben werden nur im Sitzungszustand gehalten.

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
Staffelgebühren, gemischte Steuersätze, grenzüberschreitende Fälle, Finanzierung,
Arbeitszeit, Verkaufskosten, Ertragsteuern und rechtliche Eignung eines
Steuermodus. Rundung erfolgt nur zur Anzeige; Rechnungssummen können durch
positionsweise Cent-Rundung abweichen. Vor Verwendung für echte Entscheidungen
Rechnungen, Auktionsbedingungen und steuerliche Behandlung prüfen lassen.

## iPhone: späteres Cloud-Deployment ohne lokalen PC

Empfohlener Einstieg: [Streamlit Community Cloud](https://streamlit.io/cloud),
weil die App direkt aus GitHub bereitgestellt werden kann. Der Anbieter bewirbt
einen kostenlosen Einstieg; aktuelle Konditionen, Ressourcen- und Privatprojekt-
Limits vor Anmeldung prüfen. Keine Kreditkarte oder kostenpflichtigen Tarif
aktivieren. Das private Repository nicht zur Umgehung von Limits öffentlich machen.

Die folgenden Schritte **veröffentlichen eine App** und sind eine Anleitung für
später, keine in diesem Auftrag ausgeführte Aktion:

1. In Safari den Pull Request auf GitHub prüfen. Erst nach eigener Freigabe mergen.
2. Streamlit Community Cloud öffnen und mit GitHub anmelden. Nur die benötigten
   Repository-Berechtigungen gewähren. Bei Bedarf in Safari im Seitenmenü
   „Desktop-Website anfordern“ wählen.
3. „Create app“ auswählen. Repository `pk9r872ctr-ui/Moebel-Auktionscanner`,
   Branch `main`, Einstieg `app.py`; Python 3.12 in erweiterten Einstellungen.
   Keine Secrets nötig. Bei einem Kostenhinweis stoppen.
4. **Vor „Deploy“ Sichtbarkeit und Zugriff prüfen**: nur den gewünschten privaten
   Zugriff verwenden. Wenn der Gratis-Tarif das nicht unterstützt, stoppen und
   eine Hostingentscheidung treffen. Keine echten sensiblen Daten hochladen.
5. Nach bewusster Veröffentlichungsfreigabe „Deploy“ wählen, Build-Protokoll
   prüfen und den bereitgestellten HTTPS-Link in Safari öffnen.
6. Demo-Karten, Steuermodi und manuelle Kalkulation testen. Safari → Teilen →
   „Zum Home-Bildschirm“ für schnellen Zugriff. Einstellungen bei Bedarf neu
   eingeben: kein dauerhaftes Speichern, kein Offlinebetrieb.

Offizielle Anleitungen: [Deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app),
[Zugriff und Teilen](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).
Gratis-Apps können schlafen und müssen beim Öffnen starten. Das Dashboard ist
kein dauerhafter Hintergrundscanner. Für spätere regelmäßige Abrufe sind ein
separater Worker, Persistenz, Quoten und Kostenlimits zu planen. Keine automatische
Aktivierung kostenpflichtiger Infrastruktur. Rücknahme: vorherigen geprüften
Commit wiederherstellen; Hosting-App bei Bedarf im Anbieter-Dashboard löschen.

## Architektur und echte Quellen

* `scoring.py`: reine Berechnung ohne Netzwerk oder Streamlit.
* `sources.py`: typisierter `Lot` und read-only `AuctionSource`-Protokoll.
* `sample_data.py`: ausschließlich fiktive Daten und Gebühren; keine behaupteten
  Bedingungen realer Plattformen. Frühere unbestätigte Plattform-Vorgaben entfernt.
* `app.py`: mobile Darstellung, Eingaben und getrennte Datenmodi.
* `tests/`: fachliche Regressionen und Streamlit-Interaktion.

Live-Modus liefert ausdrücklich keine Daten. Ein künftiger Adapter darf nur eine
nachweislich erlaubte API, einen genehmigten Feed oder lizenzierte Importdaten
nutzen. Vor Anschluss Nutzungsbedingungen, Zugriff, Rate-Limits und Gebühren
klären. Für echte Lose `is_demo=False` und Herkunft, Abrufzeit, Original-URL und
Gebührenbeleg liefern; unbekannte Konditionen dürfen keine Standardwerte erhalten.
API-Schlüssel nur als Hosting-Secrets, nie in Git. Kein HTML-Scraping eingebaut.
Der aktuelle MVP hat keine API-Anbindung und keine automatische Preisrecherche.

## Prüfung und verbleibende Risiken

Siehe [VALIDATION.md](VALIDATION.md) für die ausgeführten Prüfungen. CI führt die
Tests bei Push und Pull Request aus. Keine produktive Veröffentlichung, keine
Gebote, keine Dienste aktiviert. Nicht mergen, solange fachliche Annahmen für den
eigenen Steuerfall ungeklärt sind. Das MVP ist für Szenarioplanung vorbereitet;
Live-Betrieb und rechtliche/steuerliche Freigabe bleiben eigene Arbeitsschritte.
