# Helm — Devpost submission (paste-ready)

**Event**: All Things Agentic Hackathon (Google) · **Track**: The Fortified Enterprise Fleet
**Deadline**: 2026-08-31 17:00 PDT = Sep 1 01:00 BST

## Links
- **Hosted project URL**: https://helm-294160018950.europe-west1.run.app
  (one page — the whole product)
- **Repository**: https://github.com/hyperdrift-io/helm (public)
- **Protected asset (billing service)**: https://cargo-294160018950.europe-west1.run.app
- **Architecture**: `/architecture` — a live page lit by the real event stream,
  so the diagram shows the crew moving rather than a drawing of it
  (static SVG also at `/architecture.svg` and `assets/architecture.svg`)

## Google stack (required)
- **Gemini 3.5 Flash** via Vertex AI — every decision in every cycle
- **Agent Development Kit (ADK)** — the crew: `LlmAgent` + `sub_agents` routing +
  `McpToolset` with per-agent `tool_filter`
- **Google Cloud** — Cloud Run (two services), Cloud Run Admin API (the agent's
  real infrastructure actions), Firestore (the ledger)

## Tagline
A fortified agent crew at the wheel of a live product fleet — it detects,
defends, scales and heals real services with no one at the keyboard.

## Description

**The gap.** Agent demos watch a simulation. Real fleets don't get that luxury:
when a service falls over, or an attack starts, or traffic spikes, someone has
to notice and act. For a small team that someone is always the same overloaded
human. Helm is the crew that team doesn't have.

**What it does.** Helm runs a real four-app production fleet. A crew of
Gemini-powered ADK agents watches for change — an outage, an attack pattern, a
traffic surge, an exception spike in the product analytics — and closes the
loop itself: diagnose against live reality, take the one right action, verify
it worked, file the post-mortem.

**The crew, and why the split matters.** The Commander routes and holds no
tools. The Watch Officer is read-only: it verifies every event against live
probes and real PostHog telemetry, and it cannot act. The Engineer acts —
healing services, cutting ingress under attack, scaling under load through the
Cloud Run Admin API. That separation is enforced by construction: each agent's
toolset is fixed by an MCP `tool_filter`, not by a prompt it might be talked
out of. And the Engineer's power is hard-allowlisted to drill assets — ask it
to take a production app offline and the tool itself refuses and escalates to
a human. Taking a service offline at all is reserved for an attack the
diagnosis confirms: cutting a healthy service off from its users is the more
expensive mistake, so a plain outage gets healed or escalated instead.

**Real actions, not log lines.** Every control on the site causes a real effect
a judge can reproduce. *Break* makes a service serve real 500s with a prompt
injection planted in the error page; the armor screen quarantines it before
Gemini reads it, and the Engineer heals the service and verifies recovery.
*Attack* storms the cargo billing service and the Engineer cuts its Cloud Run
ingress — the public URL is dead in seconds. *Surge* floods it with real load
and the Engineer raises max instances, then proves it with a live config read.

**Why the injection beat matters.** An agent fleet reads its own telemetry, and
telemetry carries text written by the outside world — so it is an attack
surface. Helm treats anything instruction-shaped in a tool result as data to
quarantine, never orders, and every quarantine is its own ledger record.

**The page.** One page is the whole product. The orchestrator sits at the
centre as a molecule — a burning core, one node per service bonded to it, each
node a porthole onto that service's own artwork so you recognise it before you
read the label. A node is rimmed green while it holds and washes red the moment
a probe fails. Every tool call an agent makes sends a trailing light down that
service's bond, so you watch decisions travel to the service they act on. Each
card links to the real running app (these are live services, not sandboxes),
carries the same artwork as its node, and shows up to three live figures: PostHog's last hour for
the production apps — visitors, events, errors — and probe latency, requests
per minute and real Cloud Run capacity for the drill assets. Nothing is
invented: when a scan is unavailable the figure reads "—" and the card says
why. Trigger a command and the bond fires, the card flips, and progress streams
step by step to completion — on the page *and* inside the app itself, through a
one-line control client. Then the numbers move: cut cargo's ingress and the
next probe fails, so its card goes *down*; scale it and the capacity figure
changes. Cycles the watchers raise on their own light the map the same way.

**Architecture.** Watchers and webhooks raise events → the Commander routes →
the Watch Officer diagnoses → the Engineer acts through the Fleet MCP → every
event, tool call, quarantine and verdict lands on the Firestore ledger, so the
audit trail survives a restart and streams live to the page. The same code runs
self-hosted with a jsonl ledger: the MCP tool surface is the contract, and ADK
plus Gemini are its first automated client.

## Spin-up instructions
```sh
git clone https://github.com/hyperdrift-io/helm && cd helm
uv sync
gcloud auth application-default login          # Vertex AI credentials
GOOGLE_CLOUD_PROJECT=<project> GITHUB_TOKEN=<token> uv run python -m helm
# bridge on http://localhost:8080 — jsonl ledger, identical behaviour to prod
```
Deploy: `gcloud run deploy helm --source . --region europe-west1`
(env: `HELM_SANDBOX_URL`, `HELM_CARGO_URL`, `HELM_FIRESTORE_DB`,
`POSTHOG_API_KEY`, `GITHUB_TOKEN`; keep `--max-instances 1` — the watcher is
one pair of eyes.) Full detail in the README.

## Pre-existing code disclosure (per rules)
All agent, orchestration, MCP, console and service code in this repository was
written during the submission period. Pre-existing and disclosed: the four live
Hyperdrift apps that Helm watches (they are the fleet, not part of the entry),
their PostHog analytics projects, and the fleet-operations concepts this work
reimagines. Standard open-source libraries used per their licences.

## Pre-send checklist
- [x] Repo public
- [x] Architecture diagram (served + in repo)
- [x] Hosted URL live, all drills verified in production
- [x] GITHUB_TOKEN (org-scoped, Issues RW) wired — verified: agent filed issue #3 from prod
- [ ] Demo video recorded (see RECORDING.md) and uploaded
- [ ] `scripts/reset-demo.sh` run immediately before recording
- [ ] Founder review gate approved
