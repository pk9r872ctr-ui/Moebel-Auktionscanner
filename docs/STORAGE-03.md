# Speicherung und Betrieb – Auftrag 03

## Befund und Änderungen

Der alte Speicher bewahrte ausschließlich den neuesten Stand. Ältere widersprüchliche Beobachtungen waren nach einer Aktualisierung nicht mehr erkennbar. Es gab keine migrationsfähige Versionskennung, Entscheidungsbindung, Sicherung oder persistierte Laufhistorie.

Schema `PRAGMA user_version=2` ergänzt rückwärtskompatibel `observations`, `decisions` und `scan_runs` sowie `import_provenance`. Bestehende aktuelle Angebote werden atomar als erste Beobachtung übernommen. Historische Beobachtungen, die vor dieser Änderung überschrieben wurden, sind nicht rekonstruierbar. Neuere unbekannte Schemaversionen werden abgelehnt.

Identitäten bleiben `(workspace, source, source_id)`. Beobachtungszeitpunkte werden in UTC normalisiert. Jeder gültige unterschiedliche Zeitpunkt wird dauerhaft gespeichert; UPDATE/DELETE auf der Historientabelle werden durch SQLite-Trigger gesperrt. Ein gleicher Zeitpunkt mit abweichenden Daten verwirft die ganze Importtransaktion. Ältere Beobachtungen verändern den neuesten Stand nicht. Digest-Idempotenz bleibt je Arbeitsbereich erhalten: Aufrufer müssen einen vertrauenswürdig berechneten Inhaltsdigest liefern; der Datei-Scanner verwendet SHA-256 des vollständigen Imports.

## Schnittstellen

`history(workspace, source, source_id)` liefert zeitlich sortierte `Listing`-Objekte.
`set_decision(workspace, source, source_id, decision, note='', expected_observed_at=None)` erlaubt `watchlist`, `candidate`, `rejected`, `unreviewed` und bindet die Entscheidung an den aktuellen Beobachtungszeitpunkt. `decisions(workspace)` liefert Datensätze einschließlich `stale` und `review_required`. Jede spätere Beobachtung verlangt erneute Prüfung, selbst wenn sich lediglich der Erfassungszeitpunkt geändert hat. `export_candidates(workspace)` liefert ausschließlich weiterhin aktuelle Kandidatensnapshots. Die UI übergibt den angezeigten Beobachtungszeitpunkt; eine zwischenzeitliche Aktualisierung wird atomar zurückgewiesen. Direkte vertrauenswürdige Aufrufer können den optionalen Zeitpunkt weglassen. Kandidat bedeutet manuelle Auswahl, keine Kauf- oder Profitfreigabe.

`export_listings(workspace)` liefert unveränderte Importvertrags-Dictionaries; keine Lagerverwaltung oder Buchhaltung. `scan_status(workspace, limit=20)` liefert gespeicherte abgeschlossene Dateiläufe einschließlich isolierter Fehler. Dateinamen sind interne Metadaten; Unternehmensdaten und Sicherungen bleiben privat. Direkte UI-Imports sind über Digest und Historie erkennbar, erzeugen aber keinen Datei-Scannerlauf.

## Sicherung und Wiederherstellung

```python
from scanner import ListingStore, restore_backup
store = ListingStore('/private/scanner.sqlite3')
store.backup('/private/scanner-backup-2026-10-10.sqlite3')
restore_backup('/private/scanner-backup-2026-10-10.sqlite3', '/private/restored.sqlite3')
```

Die SQLite-Backup-API erzeugt einen konsistenten Snapshot. Quell- und Zieldatenbank werden anhand SQLite-Integrität, unterstützter Version, Datenvertrag, Historie und Entscheidungsreferenzen validiert. Ziele werden exklusiv mit Modus `0600` erstellt. Bestehende Dateien und Symlinks werden niemals überschrieben. Ungültige neue Sicherungen werden entfernt. Legacy-Sicherungen werden erst in der neuen Zieldatei migriert. Eine Wiederherstellung ersetzt niemals eine laufende Datenbank; Anwendung zuerst stoppen, wiederhergestellten Speicher prüfen und Konfiguration bewusst umstellen. Keine automatische Löschung oder automatische Sicherungsrotation.

## Verifikation und Grenzen

`python -m pytest tests/test_scanner.py -q` prüft Wiederanlauf, Idempotenz, Workspace-Isolation, Konflikt-Rollback, ältere Beobachtungen, unveränderliche Historie, Kandidateninvalidierung, Migration, Backup/Restore, beschädigte Daten, Symlinks und gespeicherte Laufberichte.

Der Scanner benötigt für `--watch` einen dauerhaft laufenden Prozess und beschreibbaren privaten persistenten Speicher. Ohne laufenden Rechner/Server keine 24/7-Verarbeitung. Es entstehen keine externen Kosten und keine Netzwerkabrufe. Laufhistorie und Beobachtungen wachsen ohne automatische Begrenzung; Speicherplatz überwachen und Sicherungen außerhalb des laufenden Datenträgers aufbewahren. Dateirechte ersetzen keine Verschlüsselung, Authentifizierung oder serverseitige Autorisierung: Workspace ist eine Datenpartition, kein Zugriffsschutz. SQLite bleibt für interne Einzelbenutzung geeignet; Mehrprozess-/Mehrkundenbetrieb benötigt gesonderte Last- und Zugriffsprüfung. Administrative SQL-Rechte können Trigger entfernen; die Historie ist keine kryptographische Beweiskette.

## Recherche-Provenienz (Schema v2)

Die atomare Migration v1→v2 ergänzt `import_provenance`, ohne Angebotsvertrag oder vorhandene Daten zu ändern. Optionales `batch.provenance` wird je `(workspace, digest)` als unveränderte JSON-Struktur zusammen mit der Importtransaktion gespeichert: Originalzeilen, Beschreibung, ursprüngliche Preisart und Mapping bleiben erhalten. Nicht vorhandene historische Originalzeilen werden nicht erfunden. Struktur, JSON-Kompatibilität und Importgrößenlimit werden geprüft. Wiederholte Digests verändern die gespeicherte Provenienz nicht. `import_provenance(workspace, digest)` liefert ein Tupel der Originalobjekte; `export_provenance(workspace)` exportiert diese separat vom normalisierten Angebotsvertrag. Backup/Restore bewahren Provenienz und prüfen ihre Importreferenzen. Es werden keine dieser Originaldaten als wirtschaftlich gesicherte Werte eingestuft.
