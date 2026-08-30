"""Ledger + live event bus.

The ledger is Helm's memory and audit trail: every event received and every
action taken is one record. Firestore when configured (Cloud Run demo),
local JSONL otherwise (self-hosted) — same records either way.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

_LOCAL_PATH = Path(os.environ.get("HELM_LEDGER", "data/ledger.jsonl"))
_subscribers: set[asyncio.Queue] = set()
_recent: list[dict[str, Any]] = []
_RECENT_MAX = 100

_db = None
if os.environ.get("HELM_FIRESTORE", "1") != "0" and os.environ.get("GOOGLE_CLOUD_PROJECT"):
    try:
        from google.cloud import firestore

        _db = firestore.Client(
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            database=os.environ.get("HELM_FIRESTORE_DB", "fleet-bridge"),
        )
    except Exception:
        _db = None


def backend() -> str:
    return "firestore" if _db is not None else "jsonl"


def record(kind: str, **data: Any) -> dict[str, Any]:
    """Append one record to the ledger and fan out to live subscribers."""
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "kind": kind, **data}
    if _db is not None:
        _db.collection("ledger").add({**rec, "seq": time.time_ns()})
    else:
        _LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOCAL_PATH.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    _recent.append(rec)
    del _recent[:-_RECENT_MAX]
    for q in list(_subscribers):
        try:
            q.put_nowait(rec)
        except asyncio.QueueFull:
            pass
    return rec


def recent(limit: int = 40) -> list[dict[str, Any]]:
    """The audit trail, newest last. Firestore is authoritative when configured
    so history survives a restart; memory/jsonl is the self-hosted path."""
    if _db is not None:
        try:
            docs = (_db.collection("ledger")
                    .order_by("seq", direction="DESCENDING").limit(limit).get())
            rows = [d.to_dict() for d in reversed(list(docs))]
            if rows:
                return rows
        except Exception:
            pass
        return _recent[-limit:]
    rows = _recent
    if not rows and _LOCAL_PATH.exists():
        rows = [json.loads(l) for l in _LOCAL_PATH.read_text().splitlines()[-limit:]]
    return rows[-limit:]


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)
