"""Password-encrypted backup transport; SQLite copy/validation stays in scanner.py."""
from pathlib import Path
import os
import tempfile
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from listings import ValidationError
from scanner import restore_backup

MAX_BACKUP_BYTES = 2 * 1024 * 1024  # Matches existing Streamlit upload limit.
HEADER = b'MOEBEL-BACKUP\x01'


def _key(password, salt):
    if not isinstance(password, str) or not 16 <= len(password) <= 1024:
        raise ValidationError('Backup-Passwort benötigt 16 bis 1024 Zeichen')
    return PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=600000).derive(password.encode())


def encrypted_backup(store, password):
    """Only ciphertext reaches Streamlit's download media storage."""
    with tempfile.TemporaryDirectory(prefix='scanner-backup-') as folder:
        target=store.backup(Path(folder)/'snapshot.sqlite3')
        if target.stat().st_size > MAX_BACKUP_BYTES - 128:
            raise ValidationError('Backup überschreitet 2 MiB; privates administratives Backup verwenden')
        raw=target.read_bytes()
    salt=os.urandom(16);nonce=os.urandom(12)
    return HEADER+salt+nonce+AESGCM(_key(password,salt)).encrypt(nonce,raw,HEADER)


def restore_encrypted(payload, password):
    """Validate a NEW session copy; never overwrite or reconfigure a live store."""
    if not isinstance(payload,bytes) or not len(HEADER)+44 < len(payload) <= MAX_BACKUP_BYTES or not payload.startswith(HEADER):
        raise ValidationError('Ungültiges verschlüsseltes Backup oder Dateilimit überschritten')
    start=len(HEADER);salt=payload[start:start+16];nonce=payload[start+16:start+28]
    try:
        raw=AESGCM(_key(password,salt)).decrypt(nonce,payload[start+28:],HEADER)
    except InvalidTag:
        raise ValidationError('Passwort falsch oder Backup beschädigt') from None
    if not raw.startswith(b'SQLite format 3\x00'):
        raise ValidationError('Backup enthält keine SQLite-Datenbank')
    folder=Path(tempfile.mkdtemp(prefix='scanner-session-'))
    try:
        original=folder/'upload.sqlite3'
        fd=os.open(original,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'wb') as file:file.write(raw)
        restored=restore_backup(original,folder/'restored.sqlite3')
        original.unlink()
        return str(restored)
    except Exception:
        import shutil
        shutil.rmtree(folder)
        raise
