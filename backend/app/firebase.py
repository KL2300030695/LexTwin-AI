"""Storage abstraction over Firestore + local file storage.

When USE_FIREBASE=false (default, e.g. no credentials filled in yet) this
transparently falls back to local JSON files / local disk, so the rest of
the app can be developed and tested without live Firebase credentials.
Swap in real credentials + USE_FIREBASE=true and nothing else needs to change.

Note: raw uploaded files (the original PDF/DOCX) are always kept on local
disk, even with USE_FIREBASE=true -- Cloud Storage for Firebase requires the
paid Blaze plan, while Firestore itself stays on the free Spark plan. Nothing
in this app reads the raw file back through this interface (parsing happens
once, synchronously, at upload time; every feature afterwards operates on the
parsed structured data in Firestore), so there's no functional loss.
"""
from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Any, Optional

from app.config import settings

# FastAPI runs sync endpoints in a thread pool -- several requests can reach
# get_store()'s "not yet initialized" check at the same instant (e.g. the
# workspace page's Promise.all of several parallel API calls, right after a
# fresh backend start). Without a lock, two threads can both pass the
# `_store is None` check before either finishes initializing, and the second
# firebase_admin.initialize_app() call raises "the default Firebase app
# already exists".
_init_lock = threading.Lock()

_firestore_client = None


def _init_firebase() -> None:
    global _firestore_client
    if _firestore_client is not None:
        return
    import firebase_admin
    from firebase_admin import credentials, firestore

    cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
    if not cred_path.exists():
        raise RuntimeError(
            f"USE_FIREBASE=true but credentials file not found at {cred_path}. "
            "Download a service account key from Firebase console and set "
            "FIREBASE_CREDENTIALS_PATH, or set USE_FIREBASE=false for local mode."
        )
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)
    _firestore_client = firestore.client()


class DocumentStore:
    """Key-value document store, collection/doc_id addressed, JSON-serializable values."""

    def save(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        raise NotImplementedError

    def get(self, collection: str, doc_id: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError

    def list_ids(self, collection: str) -> list[str]:
        raise NotImplementedError

    def delete(self, collection: str, doc_id: str) -> None:
        raise NotImplementedError

    def save_file(self, dest_path: str, local_file_path: str) -> str:
        """Uploads/copies a file, returns a URL or local path that can be used to retrieve it."""
        raise NotImplementedError


class LocalDocumentStore(DocumentStore):
    """Filesystem-backed store used for local dev before Firebase creds are configured."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.files_dir = base_dir / "files"
        self.files_dir.mkdir(parents=True, exist_ok=True)

    def _collection_dir(self, collection: str) -> Path:
        d = self.base_dir / collection
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        path = self._collection_dir(collection) / f"{doc_id}.json"
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def get(self, collection: str, doc_id: str) -> Optional[dict[str, Any]]:
        path = self._collection_dir(collection) / f"{doc_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_ids(self, collection: str) -> list[str]:
        d = self._collection_dir(collection)
        return sorted(p.stem for p in d.glob("*.json"))

    def delete(self, collection: str, doc_id: str) -> None:
        path = self._collection_dir(collection) / f"{doc_id}.json"
        if path.exists():
            path.unlink()

    def save_file(self, dest_path: str, local_file_path: str) -> str:
        dest = self.files_dir / dest_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_file_path, dest)
        return str(dest)


_NESTED_ARRAY_MARKER = "_array"


def _sanitize_for_firestore(value: Any) -> Any:
    """Firestore rejects an array that directly contains another array (e.g.
    our TableModel.rows: list[list[str]]) -- 'Property array contains an
    invalid nested entity'. Arrays CAN contain maps, and maps CAN contain
    arrays, so wrap any array-typed element of an array in a single-key map
    before writing. Reversed by _desanitize_from_firestore on read."""
    if isinstance(value, dict):
        return {k: _sanitize_for_firestore(v) for k, v in value.items()}
    if isinstance(value, list):
        items = [_sanitize_for_firestore(v) for v in value]
        return [{_NESTED_ARRAY_MARKER: item} if isinstance(item, list) else item for item in items]
    return value


def _desanitize_from_firestore(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value.keys()) == {_NESTED_ARRAY_MARKER}:
            return _desanitize_from_firestore(value[_NESTED_ARRAY_MARKER])
        return {k: _desanitize_from_firestore(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_desanitize_from_firestore(v) for v in value]
    return value


class FirestoreDocumentStore(DocumentStore):
    def __init__(self):
        _init_firebase()
        # Raw file storage stays local -- see module docstring.
        self._files = LocalDocumentStore(settings.LOCAL_DATA_DIR)

    def save(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        _firestore_client.collection(collection).document(doc_id).set(_sanitize_for_firestore(data))

    def get(self, collection: str, doc_id: str) -> Optional[dict[str, Any]]:
        snap = _firestore_client.collection(collection).document(doc_id).get()
        return _desanitize_from_firestore(snap.to_dict()) if snap.exists else None

    def list_ids(self, collection: str) -> list[str]:
        return [d.id for d in _firestore_client.collection(collection).stream()]

    def delete(self, collection: str, doc_id: str) -> None:
        _firestore_client.collection(collection).document(doc_id).delete()

    def save_file(self, dest_path: str, local_file_path: str) -> str:
        return self._files.save_file(dest_path, local_file_path)


_store: Optional[DocumentStore] = None


def get_store() -> DocumentStore:
    global _store
    if _store is not None:
        return _store
    with _init_lock:
        if _store is not None:  # another thread finished initializing while we waited
            return _store
        if settings.USE_FIREBASE:
            _store = FirestoreDocumentStore()
        else:
            _store = LocalDocumentStore(settings.LOCAL_DATA_DIR)
        return _store
