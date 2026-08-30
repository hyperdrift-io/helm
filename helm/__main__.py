"""Run Helm: web bridge + watchers + the orchestration loop.

Self-hosted:  python -m helm            (jsonl ledger, same behaviour)
Cloud Run:    the Dockerfile runs this  (Firestore ledger)
"""

from __future__ import annotations

import asyncio
import os

import uvicorn

from helm import agent, store, watch
from helm.web import app, events

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")


async def orchestrate() -> None:
    """One event at a time: pull, run a Helm cycle, repeat.

    Vertex's shared pool can answer 429 under load; a transient rate limit
    should not lose an incident, so the cycle is retried with backoff.
    """
    while True:
        event = await events.get()
        for attempt in range(3):
            try:
                await agent.handle_event(event)
                break
            except Exception as e:
                transient = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                if transient and attempt < 2:
                    store.record("cycle_retry", attempt=attempt + 1,
                                 reason="rate limited by the model API",
                                 event_kind=event.get("kind"))
                    await asyncio.sleep(4 * (attempt + 1))
                    continue
                store.record("cycle_error", error=f"{type(e).__name__}: {e}",
                             event_kind=event.get("kind"))
                break


async def main() -> None:
    store.record("helm_start", ledger=store.backend())
    server = uvicorn.Server(uvicorn.Config(
        app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), log_level="warning"
    ))
    await asyncio.gather(server.serve(), watch.run(events), watch.signals(events),
                         orchestrate())


if __name__ == "__main__":
    asyncio.run(main())
