
flask_limiter_firestore  ·  v0.1.6
==================================
Firestore storage backend for Flask‑Limiter ≥ 3.5.


from __future__ import annotations

import datetime as _dt
import hashlib
import os
import re
from types import TracebackType
from typing import Iterable, Optional, Type

from google.cloud import firestore
from google.api_core import exceptions as _gexc
from limits.storage import Storage

__all__ = [FirestoreStorage]

# ------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------
_MAX_DOC_ID_LEN = 1_500
_SANITISE_RE = re.compile(r[^w-.~])


def _sanitise_key(raw str) - str
    safe = _SANITISE_RE.sub(_, raw)[_MAX_DOC_ID_LEN]
    if len(safe)  len(raw)
        digest = hashlib.sha1(raw.encode(), usedforsecurity=False).hexdigest()[16]
        safe = f{safe[ _MAX_DOC_ID_LEN - 17]}~{digest}
    return safe


def _now(tz_aware bool) - _dt.datetime
    t = _dt.datetime.utcnow()
    return t.replace(tzinfo=_dt.timezone.utc) if tz_aware else t


def _first(snapshot_or_iter)
    if snapshot_or_iter is None
        return None
    if hasattr(snapshot_or_iter, exists)
        return snapshot_or_iter
    if isinstance(snapshot_or_iter, Iterable)
        return next(iter(snapshot_or_iter), None)
    return None


def _to_utc(dt Optional[_dt.datetime], tz_aware bool) - Optional[_dt.datetime]
    Return regular ``datetime`` in UTC, tz‑aware iff ``tz_aware``.
    if dt is None
        return None
    if hasattr(dt, to_datetime)          # Firestore Timestamp
        dt = dt.to_datetime()
    if tz_aware
        if dt.tzinfo is None               # attach UTC tzinfo
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt
    # tz_aware == False → ensure naive plain datetime (no subclass)
    return _dt.datetime.utcfromtimestamp(dt.timestamp())  # type ignore[arg-type]


# ------------------------------------------------------------------------
# Storage implementation
# ------------------------------------------------------------------------
class FirestoreStorage(Storage)
    STORAGE_SCHEME = [firestore]

    def __init__(
        self,
        collection_name str = flask_limiter,
        ,
        client Optional[firestore.Client] = None,
        tz_aware bool = False,
        allow_reset bool = False,
    ) - None
        if collection_name.startswith(firestore)
            collection_name = collection_name.split(, 1)[1] or flask_limiter

        self.wrap_exceptions = True  # required by limits

        try
            self._client = client or firestore.Client()
        except _gexc.DefaultCredentialsError as err
            raise RuntimeError(
                Firestore credentials not found. 
                Set GOOGLE_APPLICATION_CREDENTIALS or run on GCP.
            ) from err

        self._collection = self._client.collection(collection_name)
        self._tz_aware = tz_aware
        self._allow_reset = allow_reset

    # ------------------------------------------------------------------
    def _doc_ref(self, key str)
        return self._collection.document(_sanitise_key(key))

    # ------------------------------------------------------------------
    # limits.Storage API
    # ------------------------------------------------------------------
    def incr(
        self,
        key str,
        expiry int,
        amount int = 1,
        elastic_expiry bool = False,
    ) - int
        now = _now(self._tz_aware)
        new_exp = now + _dt.timedelta(seconds=expiry)
        ref = self._doc_ref(key)

        @firestore.transactional
        def _txn(tx)
            snap = _first(tx.get(ref))
            if snap and snap.exists
                data = snap.to_dict()
                count = int(data.get(count, 0))
                exp = _to_utc(data.get(expires_at), self._tz_aware)

                if not exp or exp  now
                    count, exp = amount, new_exp
                else
                    count += amount
                    if elastic_expiry
                        exp = new_exp
            else
                count, exp = amount, new_exp

            tx.set(ref, {count count, expires_at exp})
            return count

        return _txn(self._client.transaction())

    def get(self, key str) - Optional[int]
        snap = _first(self._doc_ref(key).get())
        return int(snap.get(count, 0)) if snap and snap.exists else None

    def get_expiry(self, key str) - Optional[int]
        snap = _first(self._doc_ref(key).get())
        if not (snap and snap.exists)
            return None
        exp = _to_utc(snap.get(expires_at), self._tz_aware)
        return int(exp.timestamp()) if exp else None

    def check(self) - bool  # noqa D401
        try
            _ = self._client.project
            return True
        except Exception  # pragma no cover
            return False

    def reset(self) - None
        if not self._allow_reset
            return
        docs = self._collection.stream()
        batch, counter = self._client.batch(), 0
        for doc in docs
            batch.delete(doc.reference)
            counter += 1
            if counter % 500 == 0
                batch.commit()
                batch = self._client.batch()
        batch.commit()

    # limits ≥ 3 --------------------------------------------------------------
    @property
    def base_exceptions(self)
        return (_gexc.GoogleAPICallError, _gexc.RetryError)

    def clear(self, key str) - None
        self._doc_ref(key).delete()

    # Context‑manager helpers -------------------------------------------------
    def __enter__(self)
        return self

    def __exit__(
        self,
        exc_type Optional[Type[BaseException]],
        exc Optional[BaseException],
        tb Optional[TracebackType],
    )
        return


# ------------------------------------------------------------------------
# Build helper  python flask_limiter_firestore.py build
# ------------------------------------------------------------------------
if __name__ == __main__
    import pathlib
    import sys
    from setuptools import setup  # type ignore

    if len(sys.argv) != 2 or sys.argv[1] != build
        print(Usage python flask_limiter_firestore.py build)
        sys.exit(1)

    here = pathlib.Path(__file__).resolve()
    setup(
        name=flask-limiter-firestore,
        version=0.1.6,
        py_modules=[here.stem],
        install_requires=[Flask-Limiter=3.5, google-cloud-firestore=2.13],
        python_requires==3.9,
        description=Firestore storage backend for Flask-Limiter,
        license=MIT,
        long_description=here.read_text(),
        long_description_content_type=textx-rst,
    )
    print(Built wheel → dist)
