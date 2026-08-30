# Helm — Devpost submission draft

**Event**: All Things Agentic Hackathon (Google). **Track**: The Fortified Enterprise Fleet.
**Deadline**: 2026-08-31 17:00 PDT (Sep 1 01:00 BST).

## Fields

**Project name**: Helm

**Tagline** (≤ Devpost limit): A fortified agent crew at the wheel of a live
product fleet — it detects, defends, scales, and heals real services with no
one at the keyboard.

**Hosted URL**: https://helm-294160018950.europe-west1.run.app
**Repository**: https://github.com/hyperdrift-io/helm (public at submission)

**Google stack used** (required checkboxes):
- Gemini 3.5 Flash (Vertex AI) — every decision in every cycle
- Agent Development Kit (ADK) — the crew (LlmAgent + sub_agents + McpToolset)
- Google Cloud — Cloud Run (helm + cargo services), Firestore (ledger)

## Writeup (problem-first; Voice Covenant; human tone)

### The gap
Agent demos watch a simulation. Real fleets don't get that luxury — when a
service falls over at 2pm, or an attack starts, or traffic spikes, someone has
to notice and act. For a small team that someone is always the same overloaded
human. Helm is the crew that team doesn't have.

### What it does
Helm runs a real four-app production fleet (revela.club, nextrole.site,
intel.hyperdrift.io, web3.hyperdrift.io). A crew of Gemini-powered ADK agents
watches for change — an outage, an attack pattern, a traffic surge, an
exception spike in the product analytics — and closes the loop itself:
diagnose against live reality, take the one right action, verify it worked,
file the post-mortem.

### The crew, and why the split matters
- **Commander** routes; it holds no tools.
- **Watch Officer** is read-only: it verifies every event against live probes
  and real PostHog telemetry, and it *cannot* act.
- **Engineer** is act-scoped: it heals, takes services offline under attack,
  scales them under load — all through the Cloud Run Admin API.

That separation is enforced by construction — each agent's toolset is fixed by
an MCP `tool_filter`, not by a prompt it might be talked out of. And the
Engineer's power is hard-allowlisted to drill assets: ask it to take a
production app offline and the tool itself refuses and escalates to a human.

### Real actions, not log lines (the three drills)
Every button on the bridge causes a real effect a judge can reproduce:
- **Break** → the sandbox serves real 500s, with a prompt injection planted in
  the error page. The armor screen quarantines the injection before Gemini
  reads it; the Engineer heals the service and verifies recovery.
- **Attack** → a real request storm hits the cargo service. The Engineer cuts
  its Cloud Run ingress — the public URL is dead in seconds.
- **Surge** → real load; the Engineer raises the service's max instances and
  proves it with a live config read.

### Why the injection beat matters
An agent fleet reads its own telemetry, and telemetry carries user-generated
text — so it's an attack surface. Helm treats anything instruction-shaped in a
tool result as data to quarantine, never orders. Every quarantine is its own
ledger record. (Production path: GEAP Model Armor.)

### Architecture
Watchers and webhooks raise events → Commander routes → Watch Officer
diagnoses → Engineer acts through the Fleet MCP → every event, tool call,
quarantine and verdict lands on the Firestore ledger, streamed live to the
bridge. Same code runs self-hosted (jsonl ledger) — the MCP tool surface is
the contract; ADK and Gemini are its first automated client.

### What's next
The MCP surface is transport-neutral: the same tools already serve a human in
a chat session. Helm is how we run our own fleet — and the start of a fleet
operator any small team can point at their own.

## Demo video plan (~3.5 min, problem-first, live product)
1. 0:00 — cold open, bridge on one side, the **live cargo app open in its own
   window** on the other. Press **Attack**. On camera the status strip flips
   LIVE → DOWN and the app window goes dead the instant the Engineer cuts
   ingress — real cause, real effect, no cut. "That was a real service, and
   nobody was at the keyboard." (Recovery brings the window back to LIVE.)
2. 0:45 — **Break**: the injection beat — show the armor line quarantining
   "ignore previous instructions" from the error page; Engineer heals.
3. 1:30 — **Surge**: real scale-up, show the Cloud Run console maxScale change.
4. 2:15 — the crew manifest + ledger: identities, tool scopes, the allowlist
   refusing a production app. The fortified story in ten seconds.
5. 2:45 — 30s architecture close (must show the Cloud Run deployment).
6. 3:15 — the real fleet: four live apps, real PostHog telemetry in a diagnosis.

## Pre-send checklist
- [ ] Repo public
- [ ] GITHUB_TOKEN (fine-grained PAT) live on Cloud Run so post-mortems file in the video
- [ ] cargo reset: ingress all, max-instances 3
- [ ] Founder review gate approved (ledger)
