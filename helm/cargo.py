"""Cargo — the crew's protected asset: a real, visible Cloud Run web app.

Not a JSON stub: a page a judge can watch live in its own window as the crew
takes it offline under attack and scales it under load. Run: python -m helm.cargo
"""

from __future__ import annotations

import math
import os
import socket
import time

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="cargo")

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cargo — live service</title>
<style>
:root { color-scheme:dark; }
body { margin:0; min-height:100vh; display:grid; place-items:center;
       background:#0b1116; color:#e8e4d8;
       font:16px/1.6 ui-monospace,'SF Mono',Menlo,monospace; }
.card { text-align:center; padding:2rem 3rem; border:1px solid #1f2c36;
        background:#111a21; }
h1 { margin:0 0 .3rem; font-size:1.6rem; letter-spacing:.05em; }
.dot { display:inline-block; width:.6rem; height:.6rem; border-radius:50%;
       background:#5fae6e; margin-right:.5rem; box-shadow:0 0 12px #5fae6e; }
.meta { color:#8a8677; font-size:.85rem; margin-top:1rem; }
b { color:#d8a03d; }
</style></head><body>
<div class="card">
<h1><span class="dot"></span>CARGO · serving</h1>
<div>request handled by instance <b>__INSTANCE__</b></div>
<div class="meta">a real Cloud Run service · under Helm's watch<br>
served __TS__ UTC</div>
</div>
<script>setTimeout(()=>location.reload(), 2000);</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    return (PAGE.replace("__INSTANCE__", socket.gethostname()[:12])
                .replace("__TS__", time.strftime("%H:%M:%S", time.gmtime())))


@app.get("/work")
async def work() -> dict:
    # a real unit of compute, so load and scaling mean something
    return {"done": sum(math.sqrt(i) for i in range(200_000)) > 0,
            "instance": socket.gethostname()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8081")),
                log_level="warning")
