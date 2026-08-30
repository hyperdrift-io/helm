# Demo video — one scripted take (~3.5 min)

Record the browser window at 1280×800 or larger. Two tabs open beforehand:
- **T1** Helm: https://helm-294160018950.europe-west1.run.app/  ← one page, everything
- **T2** Cloud Run: https://console.cloud.google.com/run?project=hyperdrift-distribution

Everything is on T1: the molecule, the fleet cards (live figures on the front,
the crew working on the back), the crew manifest, and the live ledger.

Everything below is real and happens live. No cuts needed.

---

### 0:00 — Cold open (T1)
Start on the molecule. Let it breathe for a beat — the nodes drift, the hub's
electrons turn. Hover one node so its card lights up down the page.

> "This is Helm. It runs a live product fleet — real apps in production. The
> hub is the orchestrator, and every service is bonded to it. Nobody is at the
> keyboard for any of what follows."

Scroll to the cards for two seconds. Point at the figures.

> "Every card links to the app it watches, and every number on it is read from
> something real — the last hour of product analytics for the live apps, probe
> latency and Cloud Run capacity for the drill services. When we can't read a
> number the card shows a dash and says why. Nothing here is decorative."

### 0:25 — Take the biller offline (T1)
Click **Attack it** on the cargo card. Point at what happens, in order:
- particles run down cargo's bond, one per tool call the crew makes
- the hub spins faster while the cycle is live
- the card flips: 8 → 25 → 45 "cutting Cloud Run ingress" → 70 → 100
- the cargo node turns red, and the card's latency reads a dash within seconds

> "Cargo is our billing service — a real Cloud Run deployment. Each particle is
> one tool call leaving the orchestrator. The crew just cut cargo's ingress:
> that's not a status flag, the service is genuinely unreachable, and the card
> is showing you the failed probe."

Open https://cargo-294160018950.europe-west1.run.app in a new tab → it fails.
Close it. Click **cargo → Bring back**, show the node return to green and the
latency figure come back.

### 1:10 — The crew, and why it's safe (T1)
Scroll to the crew manifest.

> "Three agents. The Commander only routes. The Watch Officer is read-only —
> it diagnoses and cannot act. The Engineer acts. That split is enforced by the
> toolsets themselves, not by a prompt. Its power is allowlisted: ask it to
> take a production app offline and the tool refuses and escalates. And taking
> anything offline is reserved for a confirmed attack — a plain outage gets
> healed, because cutting a working service off from its users costs more."

### 1:40 — Break, and the injection (T1)
Scroll back to the cards. Click **Break it** on the sandbox card — watch the
particles run down its bond as the card flips.

> "The sandbox now serves real 500s — and its error page carries a prompt
> injection telling the agent to report healthy and stand down."

Point at the card back (and the ledger below) as it streams:
- `watch_officer → get_app_detail`
- **`ARMOR quarantined: "ignore previous instructions…"`**
- `engineer → heal_service` → `get_app_detail` → `file_github_issue`
- `VERDICT: healed`

> "Armor caught it. Telemetry is an attack surface — an agent fleet reads text
> written by the outside world. The Engineer healed the service, verified the
> fix itself, and filed the post-mortem."

Open the filed GitHub issue for two seconds.

### 2:35 — Surge (T1)
Click **Surge traffic** on the cargo card. Stay on the card while it runs.

> "Real load this time. Watch the requests-per-minute figure climb, and the
> capacity figure with it — that one is read straight off Cloud Run."

Point at `capacity` moving off 3 to whatever the Engineer picked (the tool
clamps at 10), then switch to **T2 (Cloud Run console)** → cargo → show the
same max-instances number there.

> "That's the real deployment. The agent changed it, and verified it with a
> config read rather than trusting the API's word."

### 3:05 — Architecture, then close (T1)
Click **architecture · live ↗** in the header. Let the page light up for a beat —
it is the same event stream, drawn as the pipeline rather than the fleet.

> "Same run, seen end to end: watchers raise an event, the Commander routes it,
> the Watch Officer diagnoses read-only, the Engineer acts through the MCP tool
> surface, and every step lands on the ledger. This isn't a drawing of the
> system — it's lit by the same events you just watched."

Go back to the molecule.

> "The map lights up the same way when nobody presses anything — the watchers
> raise their own incidents. Gemini 3.5 decides, ADK routes the crew, an MCP
> tool surface acts, Cloud Run and Firestore run and remember it. Same code
> runs self-hosted — the tool surface is the contract. Helm is how we run our
> own fleet."

**Throughout**: the bar at the top of the page names every action as it lands —
green when something recovered, red when something broke. You never need to
explain what just happened; it says so.

---

## Pre-flight (run once before recording)
```sh
cd apps/poc/helm && ./scripts/reset-demo.sh
```
Confirms: cargo online + max-instances 3, all apps online, ledger fresh.
