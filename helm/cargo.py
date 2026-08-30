"""Cargo — the crew's protected asset: a real, separate Cloud Run service.

The attack and surge drills target this service, and the Engineer defends it
with real Cloud Run operations (ingress off, scale up). Run: python -m helm.cargo
"""

from __future__ import annotations

import math
import os
import socket

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="cargo")


@app.get("/")
async def root() -> dict:
    return {"cargo": "ok", "instance": socket.gethostname()}


@app.get("/work")
async def work() -> dict:
    # a real unit of compute, so load and scaling mean something
    return {"done": sum(math.sqrt(i) for i in range(200_000)) > 0,
            "instance": socket.gethostname()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8081")),
                log_level="warning")
