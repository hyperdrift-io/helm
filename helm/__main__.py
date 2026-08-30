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
    """One event at a time: pull, run a Helm cycle, repeat."""
    while True:
        event = await events.get()
        try:
            await agent.handle_event(event)
        except Exception as e:  # a failed cycle is itself ledger-worthy
            store.record("cycle_error", error=f"{type(e).__name__}: {e}",
                         event_kind=event.get("kind"))


async def main() -> None:
    store.record("helm_start", ledger=store.backend())
    server = uvicorn.Server(uvicorn.Config(
        app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), log_level="warning"
    ))
    await asyncio.gather(server.serve(), watch.run(events), orchestrate())


if __name__ == "__main__":
    asyncio.run(main())
