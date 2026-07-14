"""Storage abstraction over Firestore + Firebase Storage.

When USE_FIREBASE=false (default, e.g. no credentials filled in yet) this
transparently falls back to local JSON files / local disk, so the rest of
the app can be developed and tested without live Firebase credentials.
Swap in real credentials + USE_FIREBASE=true and nothing else needs to change.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Optional

from app.config import settings

_firestore_client = None
_bucket = None


def _init_firebase() -> None:
    global _firestore_client, _bucket
    if _firestore_client is not None:
        return
    import firebase_admin
    from firebase_admin import credentials, firestore, storage

    cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
    if not cred_path.exists():
        raise RuntimeError(
            f"USE_FIREBASE=true but credentials file not found at {cred_path}. "
            "Download a service account key from Firebase console and set "
            "FIREBASE_CREDENTIALS_PATH, or set USE_FIREBASE=false for local mode."
        )
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred, {"storageBucket": settings.FIREBASE_STORAGE_BUCKET})
    _firestore_client = firestore.client()
    _bucket = storage.bucket()


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


class FirestoreDocumentStore(DocumentStore):
    def __init__(self):
        _init_firebase()

    def save(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        _firestore_client.collection(collection).document(doc_id).set(data)

    def get(self, collection: str, doc_id: str) -> Optional[dict[str, Any]]:
        snap = _firestore_client.collection(collection).document(doc_id).get()
        return snap.to_dict() if snap.exists else None

    def list_ids(self, collection: str) -> list[str]:
        return [d.id for d in _firestore_client.collection(collection).stream()]

    def delete(self, collection: str, doc_id: str) -> None:
        _firestore_client.collection(collection).document(doc_id).delete()

    def save_file(self, dest_path: str, local_file_path: str) -> str:
        blob = _bucket.blob(dest_path)
        blob.upload_from_filename(local_file_path)
        blob.make_public()
        return blob.public_url


_store: Optional[DocumentStore] = None


def get_store() -> DocumentStore:
    global _store
    if _store is not None:
        return _store
    if settings.USE_FIREBASE:
        _store = FirestoreDocumentStore()
    else:
        _store = LocalDocumentStore(settings.LOCAL_DATA_DIR)
    return _store
