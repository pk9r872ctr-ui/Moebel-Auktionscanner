"""Small owner-only operations panels, rendered only after enforce_access()."""
import json
import os
import sqlite3
from datetime import datetime, timezone
import streamlit as st
from backup_transport import encrypted_backup, restore_encrypted
from scanner import ListingStore
from registry import load_registry
from research_import import P0_CORE_SOURCES
from contracts import candidate_export


def active_database():
    return st.session_state.get('_restored_database') or os.environ.get('SCANNER_DATABASE')


def storage_status():
    if st.session_state.get('_restored_database'):
        return 'Sitzungskopie aus Backup · Neustart-Persistenz nicht zugesichert'
    if os.environ.get('SCANNER_DATABASE'):
        return 'SQLite konfiguriert · tatsächliche Erreichbarkeit und Sicherung prüfen'
    return 'Nur Sitzungsvorschau · kein Datenbankspeicher konfiguriert'


def render_storage():
    if st.session_state.pop('_clear_backup_password',False):
        st.session_state.pop('backup_password',None)
    st.subheader('Gespeicherte Daten und Sicherungen')
    st.info(storage_status())
    st.warning('Streamlit Community Cloud: Lokale Dateien sind keine geprüfte Neustart-/Redeploy-Sicherung. Backup selbst herunterladen und privat aufbewahren. Passwort getrennt sichern; keine Wiederherstellung ohne Passwort.')
    database=active_database()
    if not database:
        st.caption('Dauerhaft speichern erscheint erst mit SCANNER_DATABASE oder einer geöffneten Backup-Sitzungskopie. Die Konfiguration ist eine Servereinstellung, kein Uploadfeld. Bis dahin bleiben Importe Vorschauen.')
    store=None
    try:
        store=ListingStore(database) if database else None
        if store:
            workspace=os.environ.get('SCANNER_WORKSPACE','internal')
            st.write(f'{len(store.list(workspace))} Angebote · {len(store.export_provenance(workspace))} Importe mit Provenienz · {len(store.decisions(workspace))} Entscheidungen')
            with st.expander('Importhistorie und Scannerstatus'):
                st.caption('Vorhandener Vertrag speichert Digests, keine Importuhrzeiten. Unbekannte Zeitpunkte werden nicht ergänzt. Uploadfehler sind sitzungsbezogen; Dateiläufe werden separat protokolliert.')
                st.json(store.import_status(workspace))
                st.json(store.scan_status(workspace))
    except (OSError,sqlite3.Error,ValueError):
        store=None
        st.error("Konfigurierter Speicher nicht verfügbar. Eine eigene gültige Sicherung kann unten als neue Sitzungskopie geöffnet werden.")
    try:
        password=st.text_input('Backup-Passwort (mindestens 16 Zeichen)',type='password',key='backup_password')
        st.caption('Sicherung umfasst die gesamte SQLite-Datei einschließlich aller Arbeitsbereiche, Entscheidungen, Historien und Provenienz. Nur für den vertrauenswürdigen Eigentümer; kein Mehrkunden-Backup. Upload maximal 2 MiB.')
        if store and st.button('Verschlüsselte Sicherung erstellen',key='prepare_backup'):
            st.session_state['_encrypted_backup']=encrypted_backup(store,password)
            st.session_state['_backup_created_at']=datetime.now(timezone.utc).isoformat()
            st.session_state['_clear_backup_password']=True
            st.rerun()
        if st.session_state.get('_encrypted_backup'):
            st.caption('Snapshot erstellt: '+st.session_state.get('_backup_created_at','ungeklärt')+' · nach Änderungen erneut erstellen.')
            st.download_button('Verschlüsseltes Backup in Dateien speichern',st.session_state['_encrypted_backup'],'moebel-backup.enc','application/octet-stream')
        # iOS may not recognize .enc; validate content exclusively in restore_encrypted.
        uploaded=st.file_uploader('Verschlüsseltes Backup wiederherstellen',key='restore_upload')
        confirmed=st.checkbox('Eigene vertrauenswürdige Sicherung; als neue Sitzungskopie öffnen',key='restore_confirmed')
        if st.button('Backup prüfen und Sitzungskopie öffnen',disabled=not uploaded or not confirmed,key='restore_backup'):
            restored=restore_encrypted(uploaded.getvalue(),password)
            st.session_state['_restored_database']=restored
            st.session_state.pop('_encrypted_backup',None)
            st.session_state['_clear_backup_password']=True
            st.rerun()
        if st.session_state.get('_restored_database'):
            st.caption('Nur diese Sitzung nutzt die Kopie. Ursprüngliche Datenbank und Datei-Scanner bleiben unverändert. Nach Änderungen neues Backup herunterladen; bei Neustart erneut öffnen.')
            if st.button('Zur Serverkonfiguration zurückkehren',key='restore_leave'):
                st.session_state.pop('_restored_database',None)
                st.session_state.pop('_encrypted_backup',None)
                st.rerun()
    except (OSError,sqlite3.Error,ValueError):
        st.error('Speicher oder Backup ungültig/nicht verfügbar. Passwort, Datei und Größenlimit prüfen. Keine Wiederherstellung bestätigt; ursprüngliche Datenbank unverändert.')


def render_sources():
    st.subheader('Quellen und nächste Schritte')
    st.caption('Offline-Register; keine neue Webprüfung. Öffentliche Erreichbarkeit ist keine kommerzielle Datenlizenz. Möbel-/Designrelevanz ist Recherchehypothese, kein geprüftes aktuelles Sortiment.')
    sources=load_registry()['sources']
    sources.sort(key=lambda s:(P0_CORE_SOURCES.index(s['id']) if s['id'] in P0_CORE_SOURCES else len(P0_CORE_SOURCES),s['name']))
    st.write(f'{len(sources)} Quellen · 5 Kernplattformen')
    for source in sources:
        with st.expander(('Kernquelle · ' if source['id'] in P0_CORE_SOURCES else '')+source['name']):
            access=source['data_access']
            st.link_button('Offizielle Website',source['official_website'])
            st.write('Möbel-/Designansatz: '+', '.join(source['relevant_categories']))
            labels={'permission_required':'Nutzungsfreigabe erforderlich','unresolved':'ungeklärt','unconfirmed':'nicht bestätigt','verified':'belegt','partially_verified':'teilweise geprüft','outdated':'veraltet','unknown':'unbekannt'}
            st.write('Rechte: '+labels.get(access['commercial_reuse'],access['commercial_reuse']))
            st.write(f"API: {labels.get(access['api']['status'],access['api']['status'])} · Feed: {labels.get(access['feed']['status'],access['feed']['status'])} · Export: {labels.get(access['authorized_export']['status'],access['authorized_export']['status'])}")
            st.write('Live-Adapter: '+('konfiguriert' if access['connector'] else 'nicht implementiert')+' · Freigabe: '+('dokumentiert' if access['automated_access_authorized'] else 'nicht nachgewiesen'))
            st.caption('Designrelevanz nicht modellbezogen bestätigt: '+source['economic_priority']['furniture_relevance'])
            st.info('Nächste Aktion: passenden Nutzungsumfang und berechtigten Export belegen; Losbedingungen separat prüfen. Kein automatischer Abruf freigegeben.')
            st.caption('Registerprüfung: '+source['updated_at']+' · '+labels.get(source['verification_status'],source['verification_status']))
            for evidence in source['evidence']:
                if evidence.get('url'):st.link_button('Quellenbeleg '+evidence['id'],evidence['url'])
            for uncertainty in source['uncertainties']:st.caption(uncertainty)


def render_candidates():
    st.subheader('Manuelle Auswahl und Kandidaten')
    st.info('Recherche → berechtigtes aktuelles Angebot → Produkt-/Zustandsprüfung → Marktvergleich → Vollkosten/Risiko → manuelle Auswahl. Eine Markierung ist keine wirtschaftliche Freigabe oder Kaufausführung.')
    if not active_database():
        st.warning('Keine gespeicherten Entscheidungen: Speicher konfigurieren oder eigenes Backup öffnen.')
        return
    try:
        store=ListingStore(active_database());workspace=os.environ.get('SCANNER_WORKSPACE','internal')
        for decision in store.decisions(workspace):
            with st.container(border=True):
                st.text(f"{decision['source']} / {decision['source_id']} · {decision['decision']}")
                st.caption('Erneut prüfen' if decision['review_required'] else 'Snapshotgebundene manuelle Entscheidung')
        result=candidate_export(store,workspace)
        st.write(f"{len(result['candidates'])} aktuelle manuelle Auswahlen im Export; Rentabilität nicht nachgewiesen")
        st.download_button('Manuellen ERP-Prüfexport speichern',json.dumps(result,ensure_ascii=False),'kandidaten-v1.json','application/json')
    except (OSError,sqlite3.Error,ValueError):st.error('Entscheidungen oder Export nicht verfügbar.')
