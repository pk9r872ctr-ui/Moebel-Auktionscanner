# P1 Betriebsfähigkeit – Prüfung und Bedienung

## Ausgangspunkt und Umfang

Basis `main` / `7a70032c301a75d0f7fe1c34014a8f2f94b6fad5` (PR #5),
CI erfolgreich, **216 bestehende Tests bestanden**. Import-, Speicher-,
Bewertungs-, Auth-, Quellen- und ERP-Verträge geprüft. Die Anwendung bleibt
Streamlit mit v1-Listings und SQLite-Schema2. Kein Versionswechsel,
Datenbankschemawechsel, neuer Dienst oder ERP-Projektzugriff.

Vorher fehlten nutzbare Sicherungsbedienung und sichtbarer Speicherstatus.
P0-Sperren in Speicherung/UI waren vorhanden, aber der reine Bewertungsaufruf
und der Exportvalidator erkannten den historischen Marker nicht ausdrücklich.
Diese Lücken sind geschlossen. Gespeicherte ungültige P0-Kandidaten machen ein
Backup ungültig; sie gelangen nicht durch Restore oder Kandidatenexport.

## Tatsächlich implementiert

- Navigation **Arbeitsbereich / Importe / Quellen / Speicher / Kandidaten**.
- Sichtbarer Unterschied zwischen Sitzungsvorschau, konfigurierter SQLite-Datei
  und temporärer Sitzungskopie aus Backup. Bei fehlendem/kaputtem Speicher
  bleibt die Wiederherstellung zugänglich. Keine frei eingebbare Serverpfade.
- Verschlüsselter Download und validierter Restore über die vorhandenen
  SQLite-Backup-/Restore-Routinen. Originaldatenbank wird nicht überschrieben.
- Wiederhergestellte Kopie kann nach ausdrücklicher Aktion in dieser Sitzung
  für Importe, Anzeige und Entscheidungen genutzt werden. Der Datei-Scanner
  und andere Sitzungen behalten ihre bisherige Serverkonfiguration.
- Import-Digests, Provenienzanzahl und Scannerläufe sichtbar. Der vorhandene
  Vertrag kennt für allgemeine Importe keine Uhrzeit: `imported_at=null`, keine
  erfundenen Zeitangaben. Uploadfehler sind sitzungsbezogen, Dateiläufe gespeichert.
- Alle 21 Quellen mit Rechte-, API-/Feed-/Export-, Adapter-/Freigabestatus,
  Möbel-/Designhypothese, Belegen und nächster Aktion. Die fünf Kernquellen stehen
  zuerst: RESTLOS, Hämmerle, Proventura, NetBid, Zoll-Auktion. Keine Webrecherche
  oder Aktualitätsbehauptung: das bestehende Register nennt seinen Prüfstand.
- Explizite manuelle Preis-/Nachfragerisikoaufschläge erhöhen die Zielmarge
  innerhalb der vorhandenen Vollkostenrechnung. Mindestbasis 15%; Aufschläge,
  Methode und Belege müssen ausdrücklich angegeben werden. Keine gemessenen
  Risikowahrscheinlichkeiten und keine automatische Marktpreisbewertung.
  Zielgewinn, Verkaufsdauer, Finanzierung, Vorsteuer und Bruttoliquidität
  bleiben im bisherigen Vollkostenplan. Aufschläge sind Gewinnanforderungen,
  keine zweite Kostenbuchung. Unbekannte Angaben blockieren die UI-Bewertung.

## iPhone: reproduzierbare Bedienabnahme

Voraussetzung: ein bereits vom Eigentümer freigegebener privater App-Link mit
funktionierendem OIDC und Allowlist. In diesem Auftrag wurde kein Host aktiviert.

1. Anmelden. Ohne Allowlist-Freigabe dürfen keine Navigations-, Backup-, Upload-
   oder Geschäftsdatenfunktionen erscheinen. Die vorhandene manuelle OIDC-
   Freigabe und issuer/subject-Prüfung bleiben unverändert.
2. **Speicher** öffnen. Ohne `SCANNER_DATABASE`: nur Sitzungsvorschau;
   Speichern erscheint erst mit vertrauenswürdig konfigurierter Datenbank oder
   geöffneter Backup-Sitzungskopie. Serverkonfiguration gehört nicht in Git oder
   ein frei wählbares UI-Pfadfeld.
3. **Importe**: bestehenden v1-/Recherche-/P0-Vertrag wählen, berechtigte Dateien
   aus „Dateien“ auswählen, Herkunft und Sperren prüfen. Ausdrücklich speichern,
   wenn ein Speicher aktiv ist. Zähler zeigen eingefügt/aktualisiert/unverändert
   oder übersprungen. Unbekannte Werte nicht durch Null ersetzen.
4. **Speicher**: ein starkes einzigartiges Passwort aus dem Passwortmanager
   eingeben (mindestens 16 Zeichen), „Verschlüsselte Sicherung erstellen“,
   danach „Verschlüsseltes Backup in Dateien speichern“. Snapshotzeit beachten:
   Nach Änderungen neue Sicherung erstellen. Passwort getrennt aufbewahren;
   weder in Chat/Git senden noch in OAuth-Secrets ablegen. Ohne Passwort gibt
   es keine Wiederherstellung. Nach der Aktion wird das Passwortfeld geleert.
5. Wiederherstellung: eigene `.enc`-Datei aus „Dateien“ auswählen, Passwort erneut
   eingeben, Eigentum/Vertrauen bestätigen und „Backup prüfen und Sitzungskopie
   öffnen“. Falsches Passwort, beschädigte oder unverschlüsselte Dateien werden
   abgewiesen. Der vorherige Speicher bleibt erhalten.
6. **Importe / Kandidaten**: wiederhergestellte Daten, Entscheidungen,
   Originalprovenienz und Sperren prüfen. Erneuter identischer Import wird
   übersprungen. P0 bleibt Recherche, auch nach Restore und JSON-Reimport;
   keine Kandidatenfreigabe durch Preis- oder Steuerannahmen.
7. Nach Änderungen an der Sitzungskopie wieder ein Backup herunterladen.
   „Zur Serverkonfiguration zurückkehren“ verlässt nur die Sitzungskopie.
   Ein Neustart/Redeploy kann diese Kopie und lokale Daten verlieren.

## Transport- und Speichersicherheit

Nur **Ciphertext** wird an Streamlits Download-Medienspeicher gegeben, keine
unverschlüsselte SQLite-Datei. AES-256-GCM, frischer Zufallssalt (16 Byte),
Nonce (12 Byte), PBKDF2-HMAC-SHA256 mit 600.000 Iterationen. Authentifizierter
Dateikopf schützt den binären Transport. `cryptography>=42` wird als direkte
Abhängigkeit deklariert; in der Testumgebung war bereits 50.0.0 installiert,
kein Paket-/Anwendungsversionupgrade wurde durchgeführt. Bestehende
Streamlit-Anforderung bleibt gleich. Keine eigene Verschlüsselungsprimitive.

Wiederherstellung entschlüsselt nur nach erfolgreicher Authentizitätsprüfung,
validiert SQLite-Integrität, unterstütztes Schema, Listings, Historie,
Entscheidungen und Provenienz und öffnet eine **neue** Datei. Unbekannte
Tabellen, Views, manuelle zusätzliche Indizes und unerwartete Trigger werden
abgewiesen. Begrenztes SQLite-Schrittbudget und `trusted_schema=OFF` ergänzen
bestehende Prüfungen. Unterstützt werden die von dieser Anwendung erzeugten
Schemas0–2; keine beliebigen fremden SQLite-Dateien. Neue Dateien 0600,
temporäre Ordner 0700. Kein ZIP-/Pickle-Import oder benutzerdefinierter Pfad.

Sicherung umfasst die **ganze Datenbank**, einschließlich aller Arbeitsbereiche.
Das ist ausschließlich für den vertrauenswürdigen Eigentümer im bisherigen
Einbenutzerbetrieb vorgesehen. Allowlist ist keine Rollen-/Mandantenverwaltung;
keine getrennten Kunden in derselben Datenbank betreiben. Der Mechanismus ist
kein Ersatz für Mehrkundenautorisierung, Hostschutz oder Festplattenverschlüsselung.

UI-Transport maximal **2 MiB**, passend zum bestehenden Streamlit-Uploadlimit.
Größere Datenbanken brauchen einen separat geprüften privaten administrativen
Sicherungsweg; die UI blockiert solche Downloads, statt unbrauchbare Rücksicherung
zuzusichern. Bestehende serverseitige CLI-/Python-Routinen bleiben verfügbar.

## Tests und tatsächliche Grenzen

Python 3.12.14, Streamlit 1.65.0, pytest 8.4.2, cryptography 50.0.0.
`python -m pytest -q`: **226 bestanden, 0 fehlgeschlagen** (7,81 Sekunden).
`pip check`, Python-Kompilierung und `git diff --check` bestanden.
CI-Ergebnisse und aktueller Head-SHA stehen im Pull Request.

Automatisiert: Import → SQLite → verschlüsselter Snapshot → Restore →
Dashboard; Originalprovenienz, Entscheidungen, Import-Digests, Scannerläufe,
Wiederholungsimport; falsches Passwort, manipulierte/zu große/plaintext Dateien,
unzulässige SQLite-Objekte, korrupter konfigurierter Speicher, P0-API-/Export- und
persistierte Kandidatensperren, manuelle Risikoaufschläge und Auth-Grenze.

Chromium/Playwright gegen localhost, 390×844 und 320×568: verschlüsselter Download,
Dateiupload/Restore, Anzeige der restaurierten synthetischen P0-Hinweise,
Quellen-Navigation und Layout geprüft. Kein echter iPhone-/Safari-, Google-OIDC-,
Cloud-Neustart-, Redeploy-, Mehrkunden-, Last- oder formaler Sicherheitsaudit.
Die Browserprüfung nutzt ausschließlich synthetische Daten und den bestehenden
lokalen Entwicklungsmodus. Auth-Sperren separat mit AppTest geprüft.

**Keine echte Angebots-/Marktdatenabnahme in P1.** PR #5 belegte 20 technisch
verarbeitete reale Recherchezeilen und 0 fachlich ausreichend berechtigte Angebote.
Daran ändert P1 nichts. Keine neuen Preisreferenzen, Lizenzen, Marktwerte,
rentablen Käufe, erzielten Gewinne oder Zeitersparnisse nachgewiesen.
Gebraucht-/Refurbished-/Neupreise müssen weiterhin separat belegt werden;
Angebotspreise sind keine Verkaufspreise. Es gibt noch keine echte
Marktpreis-Sammel-/Matching-Pipeline im aktuellen main. Der Rechner liefert
manuell deklarierte Szenarien, keine belastbare autonome Kaufempfehlung.

## Verbleibende Risiken und nächste Schritte

1. Nutzungsrechte für mindestens zehn aktuelle geeignete Premiumangebote
   tatsächlich nachweisen; historische P0-Daten nicht umklassifizieren.
2. Hersteller/Modell/Zustand, vergleichbare Gebraucht-/Refurbished-Preise,
   Vertriebskanal, Gebühren, Steuern und alle Vollkosten fachlich belegen.
   Solange Angaben fehlen, bleibt das wirtschaftliche Ziel unbewiesen.
3. Echten Safari-/OIDC- und privaten Hostabnahmetest mit Eigentümer durchführen,
   einschließlich Mediendownload-Zugriff, Dateisicherung und Wiederherstellung
   nach tatsächlichem Host-Neustart. Vorher keine Cloud-Persistenz zusichern.
   Bestehende JSON-Exporte bleiben unveränderte private Arbeitsdateien und sind
   nicht durch dieses neue verschlüsselte DB-Transportformat ersetzt.
4. Temporäre Sitzungskopien bleiben lokale Serverdateien bis zur Laufzeitbereinigung;
   keine automatische Retention/Überwachung/Cloud-Sicherung. Verschlüsselte
   Sicherung extern privat aufbewahren. Backend ist nicht Ende-zu-Ende-verschlüsselt.
5. Manuelle Auswahl im ERP-v1-Export ist weiterhin ausdrücklich
   `manual_not_profit_verified`. Außer P0 gibt sie allein noch keinen Nachweis,
   dass Produkt-, Markt-, Rechte- und Vollkostenprüfung abgeschlossen sind.
   Kein Versand oder ERP-Schreibzugriff. Keine Käufe oder Gebote.

Keine neuen Dienste, externen Nachrichten, Webseitenabrufe, Kosten oder Deployments;
kein Auto-Merge. Tests und Code allein beweisen keine produktive Betriebsfähigkeit.

### iPhone-Restore: Dateiauswahl ohne Erweiterungsfilter

Der Restore-Upload setzt keinen Browser-Erweiterungsfilter mehr. iOS kann die
Datei `moebel-backup.enc` deshalb unabhängig von seiner Dateityperkennung zur
Auswahl anbieten. Die Dateiendung ist kein Sicherheitsnachweis: Unverändert
prüft der Server das verschlüsselte Format, das 2-MiB-Limit, Passwort und
AES-GCM-Authentizität sowie SQLite-Integrität und Schema. Klartextdateien bleiben
unzulässig. Restore öffnet ausschließlich eine neue Sitzungskopie.

Abnahme auf dem iPhone nach freigegebener Übernahme/Bereitstellung:

1. Als freigegebener Eigentümer anmelden und **Speicher** öffnen.
2. Unter **Verschlüsseltes Backup wiederherstellen** die lokal gespeicherte
   `moebel-backup.enc` in Dateien auswählen. Sie darf nicht ausgegraut sein.
3. Backup-Passwort eingeben, die Vertrauensbestätigung aktivieren und
   **Backup prüfen und Sitzungskopie öffnen** betätigen.
4. Sitzungskopie, Daten, Entscheidungen und Importhistorie kontrollieren.
   Die bisher konfigurierte Datenbank bleibt unverändert.
5. Mit falschem Passwort oder einer beliebigen Nicht-Backup-Datei muss der
   Restore scheitern; es darf keine neue Sitzungskopie aktiviert werden.

Hotfix-Prüfung: Python 3.12.14, 231 Tests bestanden (0 fehlgeschlagen), darunter
5 neue Regressionstestfälle für den ungefilterten Upload und ungültige Inhalte.
Bestehende Tests für Manipulation, Klartext, Größenlimit, Schema, Authentifizierung
und Wiederherstellung bleiben grün. Ein echter iPhone-Dateidialog wurde in der
Entwicklungsumgebung nicht geprüft; die Geräteabnahme steht aus. Kein Deployment.
