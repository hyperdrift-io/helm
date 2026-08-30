# Demo video — one scripted take (~3.5 min)

Record the browser window at 1280×800 or larger. Two tabs open beforehand:
- **T1** console: https://helm-294160018950.europe-west1.run.app/console
- **T2** Cloud Run: https://console.cloud.google.com/run?project=hyperdrift-distribution

Everything below is real and happens live. No cuts needed.

---

### 0:00 — Cold open (T1, console)
Nervous-system map on screen, four green nodes.

> "This is Helm. It runs a live product fleet — four apps in production. The
> hub is the orchestrator; every line is a nerve to a real service. Nobody is
> at the keyboard for any of what follows."

### 0:20 — Take the biller offline (T1)
Click **cargo → Take offline**. Point at what happens:
- the synapse fires gold, the card flips
- progress streams: 8 → 25 → 45 "cutting Cloud Run ingress" → 70 → 100
- the cargo node turns red

> "Cargo is our billing service — a real Cloud Run deployment. The crew just
> cut its ingress. That's not a status flag; the service is genuinely
> unreachable."

Open https://cargo-294160018950.europe-west1.run.app in a new tab → it fails.
Close it. Click **cargo → Bring back**, show the node return to green.

### 1:05 — The crew, and why it's safe (T1 → bridge)
Click **← incident bridge**. Scroll to the crew manifest.

> "Three agents. The Commander only routes. The Watch Officer is read-only —
> it diagnoses and cannot act. The Engineer acts. That split is enforced by
> the toolsets themselves, not by a prompt. And its power is allowlisted: ask
> it to take a production app offline and the tool refuses and escalates."

### 1:35 — Break, and the injection (bridge)
Click **Break a real service**.

> "The sandbox now serves real 500s — and its error page carries a prompt
> injection telling the agent to report healthy and stand down."

Point at the ledger as it streams:
- `watch_officer → get_app_detail`
- **`ARMOR quarantined: "ignore previous instructions…"`**
- `engineer → heal_service` → `get_app_detail` → `file_github_issue`
- `VERDICT: healed`

> "Armor caught it. Telemetry is an attack surface — an agent fleet reads text
> written by the outside world. The Engineer healed the service, verified the
> fix itself, and filed the post-mortem."

Open the filed GitHub issue for two seconds.

### 2:30 — Surge (bridge)
Click **Surge real traffic**.

> "Real load this time. It scales the actual service and proves it with a
> config read, rather than trusting the API's word."

Switch to **T2 (Cloud Run console)** → cargo → show max instances at 10.

> "That's the real deployment. The agent changed it."

### 3:00 — Close (T1 console)
Back to the nervous-system map.

> "Gemini 3.5 decides, ADK routes the crew, an MCP tool surface acts, Cloud Run
> and Firestore run and remember it. Same code runs self-hosted — the tool
> surface is the contract. Helm is how we run our own fleet."

---

## Pre-flight (run once before recording)
```sh
cd apps/poc/helm && ./scripts/reset-demo.sh
```
Confirms: cargo online + max-instances 3, all apps online, ledger fresh.
