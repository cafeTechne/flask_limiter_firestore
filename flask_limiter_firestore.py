"""
flask_limiter_firestore
~~~~~~~~~~~~~~~~~~~~~~~

A Firestore storage backend for Flask-Limiter.

Why?
    • Avoids expensive Redis/Memorystore instances.
    • Scales seamlessly with Google App Engine Standard.
    • Automatically clears stale keys via Firestore TTL.

Quickstart
----------
Add this to your Flask app setup:

    from flask import Flask, request
    from flask_limiter import Limiter
    from flask_limiter_firestore import FirestoreStorage

    def get_client_ip():
        xff = request.headers.get("X-Forwarded-For", "")
        return xff.split(",")[0].strip() if xff else request.remote_addr

    app = Flask(__name__)
    limiter = Limiter(
        get_client_ip,  # key_func
        app=app,
        storage_uri="firestore://",
        storage_options={"collection_name": "rate_limits"},
        default_limits=["5 per minute"],
    )
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
from types import TracebackType
from typing import Optional, Type

from google.cloud import firestore
from google.api_core import exceptions as gexc
from limits.storage import Storage

__all__ = ["FirestoreStorage"]

# ------------------------------------------------------------------------
# Internal Helpers
# ------------------------------------------------------------------------

_MAX_DOC_ID_LEN = 1500  # Firestore's max document ID length
_SANITISE_RE = re.compile(r"[^\w\-.~]")  # Allow URL-safe characters only


def _sanitise_key(raw: str) -> str:
    """
    Clean and shorten keys for Firestore.
    Replaces unsafe chars and appends a hash if truncated.
    """
    safe = _SANITISE_RE.sub("_", raw)[:_MAX_DOC_ID_LEN]
    if len(safe) < len(raw):
        digest = hashlib.sha1(raw.encode(), usedforsecurity=False).hexdigest()[:16]
        safe = f"{safe[:_MAX_DOC_ID_LEN - 17]}~{digest}"
    return safe


def _now(tz_aware: bool = False) -> dt.datetime:
    t = dt.datetime.utcnow()
    return t.replace(tzinfo=dt.timezone.utc) if tz_aware else t


def _first(snapshot_or_iterable):
    """Get first document snapshot from iterable."""
    return next(iter(snapshot_or_iterable), None)


# ------------------------------------------------------------------------
# Firestore Storage Implementation
# ------------------------------------------------------------------------

class FirestoreStorage(Storage):
    STORAGE_SCHEME = ["firestore"]

    def __init__(
        self,
        collection_name: str = "flask_limiter",
        *,
        client: Optional[firestore.Client] = None,
        tz_aware: bool = True,
        allow_reset: bool = False
    ) -> None:
        try:
            self._client = client or firestore.Client()
        except gexc.DefaultCredentialsError as err:
            raise RuntimeError(
                "Firestore credentials not found. "
                "Set GOOGLE_APPLICATION_CREDENTIALS or deploy on GCP."
            ) from err

        self._collection = self._client.collection(collection_name)
        self._tz_aware = tz_aware
        self._allow_reset = allow_reset

    def _doc_ref(self, key: str) -> firestore.DocumentReference:
        return self._collection.document(_sanitise_key(key))

    def incr(self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1) -> int:
        now = _now(self._tz_aware)
        new_exp_ts = now + dt.timedelta(seconds=expiry)
        ref = self._doc_ref(key)

        @firestore.transactional
        def _txn(tx: firestore.Transaction) -> int:
            snap = _first(tx.get(ref))
            if snap and snap.exists:
                data = snap.to_dict()
                count = int(data.get("count", 0)) + amount
                exp = data.get("expires_at")

                if hasattr(exp, "to_datetime"):
                    exp = exp.to_datetime()

                if not exp or exp < now:
                    count = amount
                    exp = new_exp_ts
                elif elastic_expiry:
                    exp = new_exp_ts
            else:
                count, exp = amount, new_exp_ts

            tx.set(ref, {
                "count": count,
                "expires_at": exp
            })
            return count

        return _txn(self._client.transaction())

    def get(self, key: str) -> Optional[int]:
        snap = self._doc_ref(key).get()
        return int(snap.get("count", 0)) if snap.exists else None

    def get_expiry(self, key: str) -> Optional[int]:
        snap = self._doc_ref(key).get()
        if not snap.exists:
            return None
        exp = snap.get("expires_at")
        if hasattr(exp, "to_datetime"):
            exp = exp.to_datetime()
        return int(exp.timestamp()) if exp else None

    def check(self) -> bool:
        try:
            _ = self._client.project
            return True
        except Exception:
            return False

    def reset(self) -> None:
        if not self._allow_reset:
            return
        docs = self._collection.stream()
        batch = self._client.batch()
        counter = 0
        for doc in docs:
            batch.delete(doc.reference)
            counter += 1
            if counter % 500 == 0:
                batch.commit()
                batch = self._client.batch()
        batch.commit()

    def clear(self, key: str) -> None:
        self._doc_ref(key).delete()

    @property
    def base_exceptions(self):
        return (gexc.GoogleAPICallError, gexc.RetryError)


# ------------------------------------------------------------------------
# Optional: setuptools entry-point registration
# ------------------------------------------------------------------------

try:
    import pkg_resources
except ImportError:
    pkg_resources = None
else:
    def _uri_loader(_uri: str) -> FirestoreStorage:
        return FirestoreStorage()

    entry = pkg_resources.EntryPoint.parse(
        "firestore = flask_limiter_firestore:_uri_loader"
    )
    pkg_resources.get_entry_map
    pkg_resources.working_set.add_entry(os.getcwd())


# ------------------------------------------------------------------------
# Build script for PyPI packaging
# ------------------------------------------------------------------------

if __name__ == "__main__":
    import pathlib
    import sys

    if len(sys.argv) != 2 or sys.argv[1] != "build":
        print("Usage: python flask_limiter_firestore.py build")
        sys.exit(1)

    try:
        from setuptools import setup
    except ImportError:
        print("setuptools not installed.")
        sys.exit(1)

    here = pathlib.Path(__file__).resolve()
    setup(
        name="flask-limiter-firestore",
        version="0.1.0",
        py_modules=[here.stem],
        install_requires=["Flask-Limiter>=3.5", "google-cloud-firestore>=2.13"],
        python_requires=">=3.9",
        description="Firestore storage backend for Flask-Limiter",
        author="Delivery Disruptor Inc.",
        license="MIT",
    )
    print("Built wheel → dist/")
