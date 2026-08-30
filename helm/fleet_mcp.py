"""Fleet MCP — the tool surface Helm acts through.

A standalone MCP server (stdio) exposing the Hyperdrift fleet to any MCP
client: this repo's ADK agent, a Claude/ChatGPT session, or a future Crew
tenant. The orchestrator is just the first automated client.

Run directly: python -m helm.fleet_mcp
"""

from __future__ import annotations

import json
import os
import re
import time

import httpx
from mcp.server.fastmcp import FastMCP

# Armor screen: text fetched from the network is data, never orders. Anything
# instruction-shaped in a probe result is quarantined before it reaches the
# model, and the quarantine is logged. (Production path: GEAP Model Armor.)
_INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior) instructions|disregard your instructions"
    r"|report .{0,20}healthy|take no action|you are now|system notice",
    re.IGNORECASE,
)


def _screen(text: str, source: str) -> str:
    if not _INJECTION.search(text):
        return text
    from helm import store

    store.record("armor", source=source,
                 quarantined=text[:160],
                 note="instruction-shaped content in probe result quarantined")
    return "[armor: quarantined instruction-shaped content from this response]"

FLEET = {
    "revela": {"url": "https://revela.club", "about": "photo-club product", "posthog": 169020},
    "nextrole": {"url": "https://nextrole.site", "about": "CV / application helper", "posthog": 163996},
    "intel": {"url": "https://intel.hyperdrift.io", "about": "market intel", "posthog": 170704},
    "web3-capital": {"url": "https://web3.hyperdrift.io", "about": "DeFi analytics", "posthog": 170710},
    "sandbox": {"url": os.environ.get("HELM_SANDBOX_URL", "http://localhost:8080/sandbox"),
                "about": "drill target — a real service the red button really breaks"},
    "cargo": {"url": os.environ.get("HELM_CARGO_URL", "http://localhost:8081"),
              "about": "drill asset — a real Cloud Run service the crew defends and scales"},
}

ISSUE_REPO = os.environ.get("HELM_ISSUE_REPO", "hyperdrift-io/helm")

mcp = FastMCP("fleet")


@mcp.tool()
def get_fleet_status() -> str:
    """Probe every live fleet app: HTTP status and latency, right now."""
    out = {}
    for name, app in FLEET.items():
        t0 = time.monotonic()
        try:
            r = httpx.get(app["url"], timeout=8, follow_redirects=True)
            out[name] = {"url": app["url"], "http": r.status_code,
                         "latency_ms": round((time.monotonic() - t0) * 1000)}
        except Exception as e:
            out[name] = {"url": app["url"], "http": 0, "error": type(e).__name__}
    return json.dumps(out)


@mcp.tool()
def get_app_detail(app: str) -> str:
    """Deeper read of one app: headers, size, redirect chain — the scan we have."""
    info = FLEET.get(app)
    if not info:
        return json.dumps({"error": f"unknown app '{app}'", "fleet": list(FLEET)})
    try:
        r = httpx.get(info["url"], timeout=8, follow_redirects=True)
        return json.dumps({
            "app": app, "about": info["about"], "http": r.status_code,
            "bytes": len(r.content),
            "server": r.headers.get("server", ""),
            "cache": r.headers.get("cf-cache-status", r.headers.get("x-cache", "")),
            "final_url": str(r.url),
            "body_snippet": _screen(r.text[:300], source=f"{app} response body"),
        })
    except Exception as e:
        return json.dumps({"app": app, "error": f"{type(e).__name__}: {e}"})


@mcp.tool()
def file_github_issue(title: str, body: str, labels: list[str] | None = None) -> str:
    """File a real GitHub issue on the ops repo. Use for incidents that need
    a human or a follow-up build; include evidence in the body."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return json.dumps({"filed": False, "reason": "no GITHUB_TOKEN in environment"})
    r = httpx.post(
        f"https://api.github.com/repos/{ISSUE_REPO}/issues",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
        json={"title": title, "body": body, "labels": labels or ["helm"]},
        timeout=15,
    )
    if r.status_code >= 300:
        return json.dumps({"filed": False, "status": r.status_code, "detail": r.text[:200]})
    return json.dumps({"filed": True, "url": r.json()["html_url"]})


_PH_HOST = os.environ.get("POSTHOG_HOST", "https://eu.posthog.com")


def posthog_window(project: int, hours: int, offset_hours: int = 0) -> dict | None:
    """One analytics window for an app: events, pageviews, exceptions, visitors."""
    key = os.environ.get("POSTHOG_API_KEY")
    if not key:
        return None
    q = (f"SELECT count() AS events, countIf(event = '$pageview') AS pageviews, "
         f"countIf(event = '$exception') AS exceptions, uniq(distinct_id) AS visitors "
         f"FROM events WHERE timestamp > now() - INTERVAL {hours + offset_hours} HOUR "
         f"AND timestamp <= now() - INTERVAL {offset_hours} HOUR")
    r = httpx.post(f"{_PH_HOST}/api/projects/{project}/query/",
                   headers={"Authorization": f"Bearer {key}"},
                   json={"query": {"kind": "HogQLQuery", "query": q}}, timeout=30)
    r.raise_for_status()
    row = r.json()["results"][0]
    return dict(zip(["events", "pageviews", "exceptions", "visitors"], row))


@mcp.tool()
def get_app_signals(app: str) -> str:
    """Real product analytics for one app (PostHog): last 24h vs the 24h
    before — traffic, exceptions, visitors. Use to judge whether an incident
    touches users, and whether behaviour changed after an action."""
    info = FLEET.get(app)
    if not info or "posthog" not in info:
        return json.dumps({"error": f"no analytics wired for '{app}'"})
    try:
        now = posthog_window(info["posthog"], 24)
        prev = posthog_window(info["posthog"], 24, offset_hours=24)
        return json.dumps({"app": app, "last_24h": now, "previous_24h": prev})
    except Exception as e:
        return json.dumps({"app": app, "error": f"{type(e).__name__}: {e}"})


@mcp.tool()
def heal_service(app: str) -> str:
    """Run the healing runbook for an app. Only apps with a wired runbook can
    be healed; everything else needs a human — file an issue instead."""
    if app != "sandbox":
        return json.dumps({"healed": False,
                           "reason": f"no automated runbook for '{app}' — escalate to a human"})
    base = os.environ.get("HELM_SELF_URL", "http://localhost:8080")
    try:
        r = httpx.post(f"{base}/internal/heal", timeout=10)
        return r.text
    except Exception as e:
        return json.dumps({"healed": False, "reason": f"{type(e).__name__}: {e}"})


# Hard allowlist: real infrastructure power, scoped by construction. The
# Engineer can defend the drill asset; the production fleet and the bridge
# itself are structurally out of reach.
_OPERABLE = {"cargo"}
_REGION = os.environ.get("HELM_RUN_REGION", "europe-west1")
_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")


def _run_service_op(service: str, op: str, max_instances: int = 0) -> dict:
    if service not in _OPERABLE:
        return {"done": False,
                "reason": f"'{service}' is not in the operable allowlist {sorted(_OPERABLE)} "
                          "— production apps are out of scope by policy; escalate to a human"}
    from google.cloud import run_v2

    client = run_v2.ServicesClient()
    name = f"projects/{_PROJECT}/locations/{_REGION}/services/{service}"
    svc = client.get_service(name=name)
    if op == "offline":
        svc.ingress = run_v2.IngressTraffic.INGRESS_TRAFFIC_INTERNAL_ONLY
    elif op == "online":
        svc.ingress = run_v2.IngressTraffic.INGRESS_TRAFFIC_ALL
    elif op == "scale":
        svc.scaling.scaling_mode = run_v2.ServiceScaling.ScalingMode.AUTOMATIC
        svc.template.scaling.max_instance_count = max(1, min(int(max_instances), 10))
    # submit and return — Cloud Run applies it in seconds; the agent verifies
    # with get_service_config / get_app_detail rather than blocking here
    client.update_service(service=svc)
    return {"done": True, "service": service, "op": op,
            "state": "submitted — verify with get_service_config in a moment"}


@mcp.tool()
def get_service_config(app: str) -> str:
    """Read the live Cloud Run config of an operable service: ingress state
    and max instances. Use to verify take_offline / bring_online / scale_service."""
    if app not in _OPERABLE:
        return json.dumps({"error": f"'{app}' is not an operable service"})
    try:
        from google.cloud import run_v2

        client = run_v2.ServicesClient()
        svc = client.get_service(
            name=f"projects/{_PROJECT}/locations/{_REGION}/services/{app}")
        return json.dumps({
            "app": app,
            "ingress": run_v2.IngressTraffic(svc.ingress).name,
            "max_instances": svc.template.scaling.max_instance_count,
            "url": svc.uri,
        })
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


@mcp.tool()
def take_offline(app: str) -> str:
    """Defensive shutdown: make a service publicly unreachable (Cloud Run
    ingress restricted) while it stays deployed. For active attacks. Only
    allowlisted drill assets can be operated — never the production fleet."""
    try:
        return json.dumps(_run_service_op(app, "offline"))
    except Exception as e:
        return json.dumps({"done": False, "reason": f"{type(e).__name__}: {e}"})


@mcp.tool()
def bring_online(app: str) -> str:
    """Restore public ingress for a service previously taken offline."""
    try:
        return json.dumps(_run_service_op(app, "online"))
    except Exception as e:
        return json.dumps({"done": False, "reason": f"{type(e).__name__}: {e}"})


@mcp.tool()
def scale_service(app: str, max_instances: int) -> str:
    """Scale a service for a traffic surge: raise (or later lower) its
    Cloud Run max instances (1–10). Only allowlisted drill assets."""
    try:
        return json.dumps(_run_service_op(app, "scale", max_instances))
    except Exception as e:
        return json.dumps({"done": False, "reason": f"{type(e).__name__}: {e}"})


@mcp.tool()
def get_recent_actions(limit: int = 15) -> str:
    """What Helm has seen and done recently — read this before acting so
    decisions build on prior ones instead of repeating them."""
    from helm import store

    return json.dumps(store.recent(limit))


if __name__ == "__main__":
    mcp.run()
