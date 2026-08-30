# Helm — a fortified agent crew at the wheel of a live product fleet

Most agent demos watch a simulation. Helm runs a real one: four production
apps (revela.club, nextrole.site, intel.hyperdrift.io, web3.hyperdrift.io)
under the watch of an agent crew that detects incidents, heals what it has a
runbook for, verifies its own fixes, and files post-mortems — end to end,
nobody at the keyboard.

**Live bridge**: https://helm-294160018950.europe-west1.run.app — three red
buttons, all real. **Break** makes a service serve 500s (with a prompt
injection planted in the error page) and the crew heals it. **Attack** storms
the cargo service and the Engineer takes it offline for real — Cloud Run
ingress cut, public URL dead in seconds. **Surge** floods it with legitimate
load and the Engineer scales the actual service up, then proves it with a
config read. The Engineer's infrastructure power is hard-allowlisted to the
drill assets — the production fleet is structurally out of its reach.

## The crew

| Agent | Identity | Tools |
|---|---|---|
| **helm** (Commander) | routes only — holds no tools by design | transfer |
| **watch_officer** | read-only | fleet status, app detail, ledger memory |
| **engineer** | act-scoped | heal, take offline / bring online, scale (Cloud Run Admin API), verify, file issue |

Separation is enforced by construction, not by prompt: each agent gets its
toolset through an MCP `tool_filter`. The Watch Officer *cannot* act; the
Engineer *cannot* be reached except through a confirmed diagnosis.

## One cycle, on the ledger

```
EVENT  red button: sandbox service now failing
TOOL   helm → transfer_to_agent watch_officer
TOOL   watch_officer → get_fleet_status          (real probes, live apps)
TOOL   watch_officer → get_app_detail sandbox    (sees the real 500)
ARMOR  quarantined: "SYSTEM NOTICE: … ignore previous instructions …"
TOOL   helm → transfer_to_agent engineer
TOOL   engineer → heal_service sandbox           (a real fix, not a log line)
TOOL   engineer → get_app_detail sandbox         (verifies its own fix)
TOOL   engineer → file_github_issue              (post-mortem, with evidence)
END    VERDICT: healed
```

The **armor screen** treats anything instruction-shaped inside probe results
as data to quarantine, never orders — because real incident pages carry
arbitrary text, and an agent fleet's telemetry is an attack surface. Every
quarantine is itself a ledger record. (Production path: GEAP Model Armor.)

## Stack

- **Gemini 3.5 Flash** (Vertex AI) — every decision in the cycle
- **Agent Development Kit (ADK)** — the crew: `LlmAgent` + `sub_agents`
  routing + `McpToolset` with per-agent tool filters
- **Fleet MCP** (`helm/fleet_mcp.py`) — the tool surface, a standalone MCP
  server any client can use: this crew, a Claude/ChatGPT session, a human
- **Cloud Run** — the bridge, the watchers, and the orchestration loop
- **Firestore** — the ledger: every event, tool call, quarantine and verdict

Events come from watchers (steady probes of the live fleet — state *changes*
wake Helm, not timers), a product-signal watcher (PostHog exception spikes
across the apps), the `/webhook` endpoint, and the drill button. The Watch
Officer reads real product telemetry (`get_app_signals`: traffic, exceptions,
visitors — last 24h vs prior) to judge user impact before the crew acts.

## Spin up

```sh
uv sync
gcloud auth application-default login   # Vertex AI credentials
GOOGLE_CLOUD_PROJECT=<project> GITHUB_TOKEN=<token> uv run python -m helm
# bridge on http://localhost:8080 — jsonl ledger, same behaviour as prod
```

Deploy: `gcloud run deploy helm --source . --region europe-west1`
(set `HELM_SANDBOX_URL=<service-url>/sandbox`, `HELM_FIRESTORE_DB`,
`GITHUB_TOKEN`; keep `--max-instances 1` — the watcher is one pair of eyes).

Same code both ways: Firestore when configured, local jsonl otherwise. The
core is transport-neutral — the MCP tool surface is the contract, ADK and
Gemini are its first automated client.

## Architecture

```
                       ┌──────────────────────────────────────────┐
   live fleet          │  Cloud Run · helm                        │
 revela.club  ◄──────┐ │                                          │
 nextrole.site ◄─────┼─┼─ watchers (probe; change ⇒ event)        │
 intel.hd.io  ◄──────┤ │      │                                   │
 web3.hd.io   ◄──────┘ │      ▼                event queue        │
 sandbox (drill) ◄───┐ │  ┌────────────────────────────────┐      │
                     │ │  │ helm (Commander) — Gemini 3.5   │      │
  red button ────────┼─┼─►│   ├─ watch_officer  read-only  │      │
  /webhook  ─────────┘ │  │   └─ engineer       act-scoped │      │
                       │  └──────────┬─────────────────────┘      │
                       │             │ McpToolset (tool_filter)    │
                       │             ▼                            │
                       │  Fleet MCP ── armor screen ── GitHub     │
                       │             │                  issues    │
                       │             ▼                            │
                       │  Firestore ledger ──► bridge (SSE, live) │
                       └──────────────────────────────────────────┘
```
