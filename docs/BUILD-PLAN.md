# Helm — contest build plan (All Things Agentic, Devpost)

Window: built 2026-08-30, deadline 2026-08-31 17:00 PDT (Sep 1 01:00 BST).
Track: Fortified Enterprise Fleet (decided at submission; Taskmaster fallback).
Disclosed pre-existing: the four live apps being watched, and the fleet-ops
concepts (Bridge/Commander) this reimagines. All agent code new in-window.

## Done
- [x] Crew: Commander → Watch Officer (read-only) → Engineer (act-scoped), ADK sub_agents
- [x] Fleet MCP tool surface; per-agent tool_filter scoping
- [x] Real remediation loop: break (drill) → diagnose → heal → verify → post-mortem
- [x] Armor screen: injection in probe results quarantined + ledger record
- [x] Watchers (state-change events on live apps), webhook, red button
- [x] Ledger: Firestore (prod) / jsonl (self-hosted); SSE bridge UI, crew manifest
- [x] Cloud Run deploy, max-instances 1; production drill verified end to end

## Remaining
- [x] FOUNDER: Devpost account + registered (2026-08-30)
- [x] FOUNDER: fine-grained PAT (org resource owner, Issues RW) → live on Cloud Run;
      verified: the Engineer filed issues #3 and #4 from production
- [x] Repo public (github.com/hyperdrift-io/helm)
- [x] Live metrics per card (PostHog + Cloud Run capacity), molecular map,
      per-card Recraft art, interactive /architecture page
- [ ] ~3–4 min demo video: cold open on the red button, one full cycle,
      ledger + crew manifest, 30s architecture close (must show Cloud Run)
- [ ] Devpost text: problem-first writeup, Voice Covenant pass, human tone
- [ ] Founder review gate (ledger: ready-for-review) before send-off
