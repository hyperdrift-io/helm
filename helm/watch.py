"""Watchers — the events that wake Helm without anyone asking.

A steady probe of the live fleet; state changes (up→down, fast→slow,
down→up) become events on the queue. Time doesn't trigger Helm — change does.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx

from helm import store
from helm.fleet_mcp import FLEET

SLOW_MS = int(os.environ.get("HELM_SLOW_MS", "3000"))
INTERVAL = int(os.environ.get("HELM_WATCH_INTERVAL", "60"))

_last: dict[str, str] = {}


async def _probe(name: str, url: str) -> str:
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as c:
            r = await c.get(url)
        ms = (time.monotonic() - t0) * 1000
        if r.status_code >= 500:
            return "down"
        return "slow" if ms > SLOW_MS else "up"
    except Exception:
        return "down"


async def run(queue: asyncio.Queue) -> None:
    """Poll the fleet; enqueue an event on every state transition."""
    while True:
        for name, app in FLEET.items():
            state = await _probe(name, app["url"])
            prev = _last.get(name)
            _last[name] = state
            if prev is not None and state != prev:
                event: dict[str, Any] = {
                    "kind": f"app_{state}" if state != "up" else "app_recovered",
                    "app": name,
                    "url": app["url"],
                    "was": prev,
                    "source": "watcher",
                }
                store.record("event", event=event,
                             event_desc=f"watcher: {name} {event['kind']} (was {prev})")
                await queue.put(event)
        await asyncio.sleep(INTERVAL)
