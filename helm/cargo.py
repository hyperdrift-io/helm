"""Cargo — the billing service the crew protects.

A believable enterprise biller (invoices, MRR, payment runs) deployed as a
real Cloud Run service. It's the drill asset: when the crew takes it offline
under attack or scales it under load, you watch a real billing dashboard react
— so the destructive actions never touch a real user app. Run: python -m helm.cargo
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

# a settled, believable ledger — moves a little each second so it reads live
_BASE = time.time()


def _figures() -> dict:
    t = time.time() - _BASE
    return {
        "mrr": 48250 + int(t) % 40,
        "open": 12 + int(t / 3) % 5,
        "paid_today": 27 + int(t / 2) % 9,
        "run_pct": min(100, 40 + int(t * 4) % 61),
    }


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cargo · billing</title>
<style>
:root { color-scheme:dark; --sea:#0b1116; --panel:#111a21; --line:#1f2c36;
        --ink:#e8e4d8; --dim:#8a8677; --gold:#d8a03d; --ok:#5fae6e; }
* { box-sizing:border-box; }
body { margin:0; min-height:100vh; background:var(--sea); color:var(--ink);
       font:14px/1.5 ui-monospace,'SF Mono',Menlo,monospace; padding:1.1rem; }
header { display:flex; align-items:center; gap:.7rem; border-bottom:1px solid var(--line);
         padding-bottom:.8rem; }
header .mark { width:2rem; height:2rem; flex:none; }
header h1 { font-size:1.1rem; margin:0; letter-spacing:.04em; }
header h1 span { color:var(--gold); }
header .live { margin-left:auto; color:var(--ok); font-size:.8rem; }
header .live b { display:inline-block; width:.5rem; height:.5rem; border-radius:50%;
                 background:var(--ok); box-shadow:0 0 8px var(--ok); margin-right:.35rem; }
.stats { display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin:.9rem 0; }
.stat { background:var(--panel); border:1px solid var(--line); padding:.7rem .8rem; }
.stat b { display:block; font-size:1.4rem; color:var(--gold); }
.stat span { color:var(--dim); font-size:.75rem; text-transform:uppercase; letter-spacing:.1em; }
.run { background:var(--panel); border:1px solid var(--line); padding:.7rem .8rem; margin-bottom:.9rem; }
.run .bar { height:6px; background:var(--line); margin-top:.5rem; }
.run .bar>i { display:block; height:100%; background:var(--gold); }
table { width:100%; border-collapse:collapse; }
th { text-align:left; color:var(--dim); font-weight:400; font-size:.72rem;
     text-transform:uppercase; letter-spacing:.1em; border-bottom:1px solid var(--line); padding:.4rem 0; }
td { padding:.4rem 0; border-bottom:1px solid var(--line); }
td.paid { color:var(--ok); } td.due { color:var(--gold); }
footer { color:var(--dim); font-size:.75rem; margin-top:.8rem; }
</style></head><body>
<header>
  __MARK__
  <h1>CARGO<span> · billing</span></h1>
  <span class="live"><b></b>serving · __INSTANCE__</span>
</header>
<div class="stats">
  <div class="stat"><b>$__MRR__</b><span>MRR</span></div>
  <div class="stat"><b>__OPEN__</b><span>open invoices</span></div>
  <div class="stat"><b>__PAID__</b><span>paid today</span></div>
</div>
<div class="run">nightly payment run <i>#4471</i>
  <div class="bar"><i style="width:__RUN__%"></i></div></div>
<table><thead><tr><th>invoice</th><th>account</th><th>amount</th><th>status</th></tr></thead>
<tbody>
<tr><td>INV-9042</td><td>Northwind Ltd</td><td>$2,400</td><td class="paid">paid</td></tr>
<tr><td>INV-9043</td><td>Acme Freight</td><td>$1,180</td><td class="due">due</td></tr>
<tr><td>INV-9044</td><td>Blue Harbor</td><td>$3,950</td><td class="paid">paid</td></tr>
<tr><td>INV-9045</td><td>Cedar Logistics</td><td>$860</td><td class="due">due</td></tr>
</tbody></table>
<footer>a real Cloud Run service · under Helm's watch · __TS__ UTC</footer>
<script>setTimeout(()=>location.reload(), 2000);</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    f = _figures()
    return (PAGE.replace("__MARK__", _MARK)
                .replace("__INSTANCE__", socket.gethostname()[:12])
                .replace("__MRR__", f"{f['mrr']:,}")
                .replace("__OPEN__", str(f["open"]))
                .replace("__PAID__", str(f["paid_today"]))
                .replace("__RUN__", str(f["run_pct"]))
                .replace("__TS__", time.strftime("%H:%M:%S", time.gmtime())))


@app.get("/work")
async def work() -> dict:
    # a real unit of compute (a billing calc), so load and scaling mean something
    return {"invoiced": sum(math.sqrt(i) for i in range(200_000)) > 0,
            "instance": socket.gethostname()}


# the Recraft mark, inlined at build time (falls back to a simple glyph)
_MARK = os.environ.get("CARGO_MARK_SVG") or (
    '<svg class="mark" viewBox="0 0 32 32" fill="none" stroke="#d8a03d" '
    'stroke-width="1.6"><rect x="6" y="9" width="20" height="15"/>'
    '<path d="M6 14h20M12 9v15"/></svg>')

try:
    _p = os.path.join(os.path.dirname(__file__), "..", "assets", "cargo-mark.svg")
    with open(_p) as _fh:
        _svg = _fh.read()
    _MARK = _svg.replace("<svg", '<svg class="mark"', 1)
except Exception:
    pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8081")),
                log_level="warning")
