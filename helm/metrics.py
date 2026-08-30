"""Live per-app numbers for the bridge cards.

At most three metrics per service, each read from something real: an HTTP probe
plus the Cloud Run config for the drill assets, PostHog's last hour for the live
apps. When the crew acts — cuts cargo's ingress, scales it, heals the sandbox —
these are the numbers that move on the card. Nothing is synthesised: when a
source is unavailable the metric reads "—" and the note says why.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

import httpx

from helm.fleet_mcp import FLEET, _OPERABLE, _PROJECT, _REGION, posthog_window

_DASH = "—"
_DRILL = {"cargo", "sandbox"}
_SLOW_MS = 1500

_cache: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_requests: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=10_000))


def note_request(app: str) -> None:
    """Record one request against an app — load generators and proxies call this."""
    _requests[app].append(time.monotonic())


def _req_per_min(app: str) -> int:
    q = _requests.get(app)
    if not q:
        return 0
    cut = time.monotonic() - 60
    while q and q[0] < cut:
        q.popleft()
    return len(q)


async def _cached(key: str, ttl: float, load: Callable[[], Awaitable[Any]]) -> Any:
    """Serve a fresh value, else the last good one, else None. Never raises."""
    hit = _cache.get(key)
    if hit and time.monotonic() < hit[0]:
        return hit[1]
    async with _locks[key]:
        hit = _cache.get(key)
        if hit and time.monotonic() < hit[0]:
            return hit[1]
        try:
            value = await load()
        except Exception:
            return hit[1] if hit else None
        _cache[key] = (time.monotonic() + ttl, value)
        return value


def _metric(label: str, value: str, unit: str = "") -> dict[str, str]:
    return {"label": label, "value": value, "unit": unit}


async def _probe(url: str) -> dict[str, Any]:
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=6) as c:
            r = await c.get(url)
        return {"http": r.status_code, "ms": round((time.monotonic() - t0) * 1000)}
    except Exception as e:
        # a refused or timed-out probe IS the reading — never fall back to a
        # stale one, that's the moment the card is supposed to move
        return {"http": 0, "ms": None, "error": type(e).__name__}


def _max_instances(app: str) -> int:
    from google.cloud import run_v2

    client = run_v2.ServicesClient()
    svc = client.get_service(
        name=f"projects/{_PROJECT}/locations/{_REGION}/services/{app}")
    return svc.template.scaling.max_instance_count


def _status(probe: dict[str, Any]) -> str:
    http = probe.get("http", 0)
    if not http:
        return "down"
    if http >= 500:
        return "failing"
    if http >= 400:
        return "warn"
    ms = probe.get("ms")
    return "slow" if ms is not None and ms > _SLOW_MS else "up"


async def _probe_snapshot(app: str) -> dict[str, Any]:
    url = FLEET[app]["url"]
    probe = await _cached(f"probe:{app}", 3, lambda: _probe(url)) or {}
    ms = probe.get("ms")
    metrics = [_metric("latency", str(ms) if ms is not None else _DASH, "ms"),
               _metric("req/min", str(_req_per_min(app)))]
    if app in _OPERABLE:
        cap = await _cached(f"run:{app}", 20,
                            lambda: asyncio.to_thread(_max_instances, app))
        if cap is not None:
            metrics.append(_metric("capacity", str(cap), "inst"))
    http = probe.get("http", 0)
    note = f"HTTP {http} · live probe" if http else \
        f"unreachable · {probe.get('error', 'no probe yet')}"
    return {"app": app, "status": _status(probe), "metrics": metrics, "note": note}


async def _signal_snapshot(app: str) -> dict[str, Any]:
    project = FLEET[app]["posthog"]
    win = await _cached(f"posthog:{app}", 60,
                        lambda: asyncio.to_thread(posthog_window, project, 1))
    if not win:
        reason = ("no POSTHOG_API_KEY" if not os.environ.get("POSTHOG_API_KEY")
                  else "PostHog did not answer")
        return {"app": app, "status": "unknown",
                "metrics": [_metric("visitors", _DASH, "/h"),
                            _metric("events", _DASH, "/h"),
                            _metric("errors", _DASH, "/h")],
                "note": f"analytics scan unavailable · {reason}"}
    return {
        "app": app,
        "status": "warn" if win["exceptions"] else "up",
        "metrics": [_metric("visitors", str(win["visitors"]), "/h"),
                    _metric("events", str(win["events"]), "/h"),
                    _metric("errors", str(win["exceptions"]), "/h")],
        "note": "PostHog · last hour",
    }


async def snapshot(app: str) -> dict[str, Any]:
    """The card strip for one app: status plus up to three live metrics."""
    info = FLEET.get(app)
    if info is None:
        return {"app": app, "status": "unknown", "metrics": [],
                "note": f"'{app}' is not in the fleet"}
    if app in _DRILL or "posthog" not in info:
        return await _probe_snapshot(app)
    return await _signal_snapshot(app)


async def all_snapshots() -> dict[str, dict[str, Any]]:
    """Every fleet app at once — the poll the bridge makes every few seconds."""
    names = list(FLEET)
    rows = await asyncio.gather(*(snapshot(n) for n in names))
    return dict(zip(names, rows))
