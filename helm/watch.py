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


async def signals(queue: asyncio.Queue) -> None:
    """Product-signal watch: an exception spike in any app wakes Helm."""
    from helm.fleet_mcp import posthog_window

    interval = int(os.environ.get("HELM_SIGNAL_INTERVAL", "1800"))
    while True:
        for name, app in FLEET.items():
            if "posthog" not in app:
                continue
            try:
                now = await asyncio.to_thread(posthog_window, app["posthog"], 1)
                prev = await asyncio.to_thread(posthog_window, app["posthog"], 1, 1)
            except Exception:
                continue
            if now and prev is not None and now["exceptions"] > max(2, 2 * prev["exceptions"]):
                event: dict[str, Any] = {
                    "kind": "exception_spike", "app": name, "source": "signal_watcher",
                    "last_hour": now, "previous_hour": prev,
                }
                store.record("event", event=event,
                             event_desc=f"signals: {name} exception spike "
                                        f"({prev['exceptions']} → {now['exceptions']}/h)")
                await queue.put(event)
        await asyncio.sleep(interval)


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
