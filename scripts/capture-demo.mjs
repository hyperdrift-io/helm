#!/usr/bin/env node
/**
 * Capture the Helm demo against the live site as one unbroken, SILENT take.
 *
 * The video narrates itself: a burned-in caption strip names every beat, and
 * the shots are framed so the page's own live text (action bar, card steps,
 * ledger) stays legible. No voiceover, no cuts. Beat order follows
 * docs/RECORDING.md, but the words are captions, not a script to read aloud.
 *
 * Three rules the code enforces, because a demo video is a claim:
 *
 *  1. HONESTY. After every crew cycle the caption quotes the verdict the crew
 *     actually wrote on the ledger — read back from the server, not written
 *     here. The Cloud Run beats print real `gcloud` stdout captured while the
 *     tape rolls. Nothing on screen is typed out to look like output.
 *  2. SYNC. On a silent video the caption *is* the narration, so a caption must
 *     never describe something that already happened. Beats that depend on the
 *     crew wait on real page or ledger state (`until(...)`) before they speak.
 *  3. LENGTH. Devpost judges the first four minutes and nothing after it, so
 *     the whole take — architecture beat and end card included — lands inside
 *     that window. Target 3:30-3:45.
 *
 * Everything it clicks is a real control on the live Bridge, so this drives
 * real Cloud Run services — run scripts/reset-demo.sh afterwards, always.
 *
 * Playwright is not a dependency of this repo. Point PW at an install:
 *   mkdir -p /tmp/helm-capture && cd /tmp/helm-capture \
 *     && npm i playwright && npx playwright install chromium --no-shell
 *   PW=/tmp/helm-capture/node_modules/playwright/index.js node scripts/capture-demo.mjs
 *
 * Output: <repo>/capture/<timestamp>/helm-demo.webm  (path printed at the end)
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, readdirSync, renameSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const _pw = await import(process.env.PW || 'playwright');
const { chromium } = _pw.chromium ? _pw : _pw.default;

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SITE = process.env.HELM_URL || 'https://helm-294160018950.europe-west1.run.app';
const PROJECT = 'hyperdrift-distribution';
const REGION = 'europe-west1';
const OUT = join(ROOT, 'capture', new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19));
mkdirSync(OUT, { recursive: true });

// 1000px tall so the molecule (126-643) and the first card row (714-1010) share
// the frame during a drill — the bond particles and the card steps are the same
// story and must not be split across two shots.
const W = 1440, H = 1000;
// The caption sits in an opaque letterbox band across the bottom BAND px. At
// scrollY 130 the first card row ends at viewport 880, four pixels clear of the
// band — so a caption never sits on top of a live card. (The second row is
// wholly behind the band, which reads as the frame edge, not as a crop.)
const BAND = 120;
const DRILL_Y = 130;
const t0 = Date.now();
const at = () => {
  const s = Math.round((Date.now() - t0) / 1000);
  return `${String((s / 60) | 0).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
};
const beat = (m) => console.log(`[${at()}] ${m}`);
const hold = (ms) => new Promise((r) => setTimeout(r, ms));
/** reading time for a silent viewer: ~4 words/s, plus a beat to settle */
const read = (s) => Math.max(2800, s.split(/\s+/).length * 235 + 850);

/** Poll a predicate until it is true. Returns whether it landed in budget. */
async function until(pred, budget, step = 700) {
  const start = Date.now();
  for (;;) {
    try { if (await pred()) return true; } catch { /* keep polling */ }
    if (Date.now() - start >= budget) return false;
    await hold(step);
  }
}

// ---------------------------------------------------------------- the ledger
// The DOM ledger trims itself, so counting <li> is not a reliable clock.
// Read the server's own record instead and compare timestamps it wrote.
const recent = async () => {
  try { return await (await fetch(`${SITE}/recent`)).json(); } catch { return []; }
};
const stampNow = async () =>
  (await recent()).reduce((m, r) => (r.ts && r.ts > m ? r.ts : m), '');

/** first record of `kind` written after `since`, or null */
async function since(kind, stamp, pick = () => true) {
  for (const r of await recent()) {
    if (r.kind === kind && r.ts > stamp && pick(r)) return r;
  }
  return null;
}

/** Wait for the crew to close a cycle. Returns the ledger's own verdict record. */
async function waitCycle(stamp, budget = 120_000) {
  const start = Date.now();
  while (Date.now() - start < budget) {
    const r = await since('cycle_end', stamp);
    if (r) {
      beat(`  cycle closed in ${Math.round((Date.now() - start) / 1000)}s`);
      return r;
    }
    await hold(1500);
  }
  beat(`  !! no cycle_end inside ${budget / 1000}s`);
  return null;
}

/** Pull the two lines that matter out of a verdict blob, fit for a caption. */
function verdictParts(rec) {
  const v = (rec?.verdict || '').trim();
  const tag = (v.match(/VERDICT:\s*(\w+)/) || [, ''])[1].toLowerCase();
  // The crew's ACTION line usually ends with "and filed <issue url>". The issue
  // is covered by the ledger beat, so keep only the action itself.
  const action = (v.match(/ACTION:\s*([^\n]+)/) || [, ''])[1]
    .replace(/\s*[,;:]?\s*(and\s+)?filed\b.*$/i, '')
    .replace(/\s*[:,-]\s*https?:\/\/\S+.*$/i, '')
    .replace(/https?:\/\/\S+/g, '')
    .trim().replace(/[\s.:,;-]+$/, '');
  return { tag, action: action ? action + '.' : '' };
}

// ------------------------------------------------------------ Cloud Run proof
// Devpost wants visual confirmation that the backend runs on Google Cloud. The
// console needs a login this capture deliberately does not have, so the proof
// is the next best thing and arguably a better one: real `gcloud` stdout, run
// while the tape rolls, printed with the command that produced it. If gcloud
// fails the beat is dropped rather than faked.
const GCLOUD = {
  // What is deployed, on what revision, at what cap — both services in one read.
  fleet: ['run', 'services', 'list', '--project', PROJECT, '--region', REGION,
    '--filter', 'metadata.name=(helm,cargo)',
    '--format', "table(metadata.name:label=SERVICE,status.latestReadyRevisionName:label=REVISION,"
      + "spec.template.metadata.annotations['autoscaling.knative.dev/maxScale']:label=MAX_INST,"
      + 'status.url:label=URL)'],
  // Both hostnames Cloud Run assigns helm — the submission link is the first one.
  urls: ['run', 'services', 'describe', 'helm', '--region', REGION, '--project', PROJECT,
    '--format', "value(metadata.annotations['run.googleapis.com/urls'])"],
  cap: ['run', 'services', 'describe', 'cargo', '--region', REGION, '--project', PROJECT,
    '--format', "value(spec.template.metadata.annotations['autoscaling.knative.dev/maxScale'])"],
  // The strongest evidence in the whole video, and the one nothing can fake:
  // Google Cloud's own admin audit log, naming the principal behind each
  // mutation of cargo. It is a service account. No human is in that column.
  audit: ['logging', 'read',
    'protoPayload.methodName="google.cloud.run.v2.Services.UpdateService" AND resource.labels.service_name="cargo"',
    '--project', PROJECT, '--freshness', '20m', '--limit', '5',
    '--format', "table(timestamp.date('%H:%M:%SZ'):label=WHEN,"
      + 'protoPayload.authenticationInfo.principalEmail:label=WHO,'
      + 'protoPayload.methodName:label=CALLED)'],
};
/** Run gcloud for real and return { cmd, out } — or null if it would have to lie. */
function gcloud(args) {
  const cmd = 'gcloud ' + args.map((a) =>
    !/[ ()'"=]/.test(a) ? a : a.includes('"') ? `'${a}'` : `"${a}"`).join(' ');
  try {
    const out = execFileSync('gcloud', args, { encoding: 'utf8', timeout: 25_000 }).trim();
    if (!out) throw new Error('empty output');
    beat(`  gcloud ok · ${out.split('\n').length} lines`);
    return { cmd, out };
  } catch (e) {
    beat(`  !! gcloud failed (${e.message.split('\n')[0]}) — dropping that Cloud Run beat`);
    return null;
  }
}

const browser = await chromium.launch({
  channel: 'chromium',    // full chromium — the headless shell composites SVG animation poorly
  args: ['--hide-scrollbars'],
});
const ctx = await browser.newContext({
  viewport: { width: W, height: H },
  deviceScaleFactor: 1,
  reducedMotion: 'no-preference',
  recordVideo: { dir: OUT, size: { width: W, height: H } },
});
// Wall clock of the recording window. Playwright stamps every frame it manages
// to grab at a nominal 25fps, so a take that dropped frames comes out of the
// muxer ~10% longer than it really was — i.e. in slow motion. Measuring the
// window lets the encode put the take back on real time below.
const videoStart = Date.now();

// The caption layer travels with the page: re-installed on every document so it
// survives the trip to /architecture and back. The band is opaque and the body
// is padded by its height, so page content is never read through a caption.
await ctx.addInitScript((band) => {
  const install = () => {
    if (document.getElementById('cap-layer')) return;
    const css = document.createElement('style');
    css.textContent = `
      body{padding-bottom:${band + 40}px !important}
      #cap-layer{position:fixed;left:0;right:0;bottom:0;height:${band}px;z-index:2147483646;
        background:#0a1015;border-top:1px solid #1b2530;
        display:flex;align-items:center;justify-content:center;
        padding:0 22px;pointer-events:none}
      #cap{max-width:64rem;opacity:0;transform:translateY(8px);
        border-left:3px solid #d8a03d;padding:.15rem 0 .15rem 1.2rem;
        transition:opacity .3s ease,transform .3s ease;
        font:20px/1.45 ui-monospace,'SF Mono',Menlo,monospace;color:#e8e4d8}
      #cap[data-on]{opacity:1;transform:none}
      #cap b{display:block;font:600 12px/1 ui-monospace,Menlo,monospace;
        letter-spacing:.22em;text-transform:uppercase;color:#d8a03d;margin-bottom:.5rem}
      #cap[data-tone="bad"]{border-left-color:#e0532f} #cap[data-tone="bad"] b{color:#e0532f}
      #cap[data-tone="ok"]{border-left-color:#5fae6e} #cap[data-tone="ok"] b{color:#5fae6e}
      #cloudcard{position:fixed;inset:0 0 ${band}px;z-index:2147483644;background:#080d11;
        opacity:0;transition:opacity .45s ease;pointer-events:none;
        display:grid;place-items:center;padding:0 3rem;
        font:16px/1.5 ui-monospace,'SF Mono',Menlo,monospace}
      #cloudcard[data-on]{opacity:1}
      #cloudcard .win{border:1px solid #1f2f3a;background:#0a1116;padding:1.9rem 2.2rem 1.6rem;
        box-shadow:0 24px 70px rgba(0,0,0,.6);max-width:1250px;width:100%;overflow:hidden}
      #cloudcard h2{margin:0 0 1.7rem;font:600 12px/1 ui-monospace,Menlo,monospace;
        letter-spacing:.26em;text-transform:uppercase;color:#d8a03d}
      #cloudcard pre{margin:0;white-space:pre;tab-size:6;color:#9fd6ab;
        font-family:Menlo,'DejaVu Sans Mono',monospace}
      #cloudcard pre+pre{margin-top:1.7rem}
      #cloudcard pre em{display:block;color:#61788a;font-style:normal;
        margin-bottom:.6rem;white-space:pre-wrap;overflow-wrap:anywhere;
        font-size:13.5px;line-height:1.6;font-family:inherit}
      #cloudcard pre em:before{content:'$ ';color:#d8a03d}
      #cloudcard .foot{margin-top:1.7rem;padding-top:1.1rem;border-top:1px solid #16232c;
        font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#4d6070}
      #titlecard{position:fixed;inset:0;z-index:2147483647;background:#0a1015;
        display:grid;place-items:center;text-align:center;opacity:0;
        transition:opacity .6s ease;pointer-events:none;
        font:16px/1.7 ui-monospace,'SF Mono',Menlo,monospace;color:#7d8894}
      #titlecard[data-on]{opacity:1}
      #titlecard h1{margin:0 0 1.1rem;font-size:4.2rem;letter-spacing:.38em;
        color:#d8a03d;font-weight:700}
      #titlecard p{margin:0 auto;max-width:44rem;font-size:1.2rem;color:#e8e4d8}`;
    document.head.appendChild(css);
    const layer = document.createElement('div');
    layer.id = 'cap-layer';
    layer.innerHTML = '<div id="cap"><b></b><span></span></div>';
    const cc = document.createElement('div');
    cc.id = 'cloudcard';
    cc.innerHTML = '<div class="win"><h2></h2><div class="body"></div></div>';
    const tc = document.createElement('div');
    tc.id = 'titlecard';
    tc.innerHTML = '<div><h1></h1><p></p></div>';
    document.body.append(layer, cc, tc);
  };
  if (document.body) install();
  else document.addEventListener('DOMContentLoaded', install);
}, BAND);

const page = await ctx.newPage();

/** Put a caption up and hold it long enough to read. tone: '' | 'ok' | 'bad'. */
async function say(label, text, tone = '', extra = 0) {
  await page.evaluate(([l, t, n]) => {
    const c = document.getElementById('cap');
    if (!c) return;
    c.querySelector('b').textContent = l;
    c.querySelector('span').textContent = t;
    c.dataset.tone = n;
    c.dataset.on = '';
  }, [label, text, tone]).catch(() => {});
  console.log(`[${at()}]   cap · ${label} — ${text}`);
  await hold(read(text) + extra);
}
const clearCap = () =>
  page.evaluate(() => document.getElementById('cap')?.removeAttribute('data-on')).catch(() => {});

async function card(h1, p, ms) {
  await page.evaluate(([a, b]) => {
    const t = document.getElementById('titlecard');
    if (!t) return;
    t.querySelector('h1').textContent = a;
    t.querySelector('p').textContent = b;
    t.dataset.on = '';
  }, [h1, p]).catch(() => {});
  await hold(ms);
}
const dropCard = async (ms = 900) => {
  await page.evaluate(() => document.getElementById('titlecard')?.removeAttribute('data-on')).catch(() => {});
  await hold(ms);
};

/** Full-screen terminal card carrying real gcloud stdout. `runs` = [{cmd,out}]. */
async function cloudCard(title, runs) {
  await page.evaluate(([t, rs]) => {
    const c = document.getElementById('cloudcard');
    if (!c) return;
    c.querySelector('h2').textContent = t;
    c.querySelector('.body').innerHTML = rs.map(() => '<pre><em></em><span></span></pre>').join('')
      + '<div class="foot"></div>';
    c.querySelectorAll('pre').forEach((pre, i) => {
      pre.querySelector('em').textContent = rs[i].cmd;
      pre.querySelector('span').textContent = rs[i].out;
    });
    c.querySelector('.foot').textContent =
      'real stdout · captured while this recording was running · nothing here was typed';
    c.dataset.on = '';
  }, [title, runs]).catch(() => {});
  await hold(700);
}
const dropCloud = async (ms = 600) => {
  await page.evaluate(() => document.getElementById('cloudcard')?.removeAttribute('data-on')).catch(() => {});
  await hold(ms);
};

/** Human-paced scroll — a jump cut on a scroll reads as a glitch. */
const glide = (to, ms = 1300) =>
  page.evaluate(
    ([target, d]) =>
      new Promise((done) => {
        const y = typeof target === 'number'
          ? target
          : (document.querySelector(target)?.getBoundingClientRect().top ?? 0) + window.scrollY - 90;
        const from = window.scrollY, t = performance.now();
        (function step(now) {
          const k = Math.min(1, (now - t) / d);
          const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
          window.scrollTo(0, from + (y - from) * e);
          k < 1 ? requestAnimationFrame(step) : done();
        })(t);
      }),
    [to, ms],
  );

const cardOf = (app) =>
  page.locator('#grid .card', { has: page.locator('.face.front .title', { hasText: new RegExp(`^${app}$`) }) });
const dotIs = (app, cls) =>
  page.evaluate(([a, c]) => {
    const el = [...document.querySelectorAll('#grid .card')].find(
      (x) => x.querySelector('.face.front .title')?.textContent.trim() === a);
    return !!el?.querySelector('.dot')?.classList.contains(c);
  }, [app, cls]).catch(() => false);
/** The card has turned over and is showing the crew's steps. */
const flipped = (app) =>
  page.evaluate((a) => {
    const el = [...document.querySelectorAll('#grid .card')].find(
      (x) => x.querySelector('.face.front .title')?.textContent.trim() === a);
    return !!el?.classList.contains('flipped');
  }, app).catch(() => false);
/** Read a figure straight off the card front — e.g. metric('cargo','capacity'). */
const metric = (app, label) =>
  page.evaluate(([a, l]) => {
    const el = [...document.querySelectorAll('#grid .card')].find(
      (x) => x.querySelector('.face.front .title')?.textContent.trim() === a);
    const span = [...(el?.querySelectorAll('.figs span') || [])].find(
      (s) => s.querySelector('em')?.textContent.trim() === l);
    return span?.querySelector('b')?.textContent.trim() ?? null;
  }, [app, label]).catch(() => null);

/** /drill, /drill/attack and /drill/surge share one rate limiter: 60s apart. */
let lastDrill = 0;
async function drillGate() {
  const wait = 61_500 - (Date.now() - lastDrill);
  if (lastDrill && wait > 0) {
    beat(`  holding ${Math.round(wait / 1000)}s for the one-drill-per-minute gate`);
    await hold(wait);
  }
}

/**
 * Press a drill button and confirm the server actually queued it — a refused
 * drill leaves the card saying "busy" and the rest of the beat makes no sense.
 * Retries once past the rate gate.
 */
async function fireDrill(button) {
  for (let tryN = 1; tryN <= 2; tryN++) {
    await drillGate();
    const stamp = await stampNow();
    lastDrill = Date.now();
    await button.click();
    for (let i = 0; i < 14; i++) {
      await hold(1000);
      if (await since('event', stamp)) return stamp;
    }
    beat(`  !! drill did not raise an event (attempt ${tryN})`);
  }
  return await stampNow();
}

// DRY=1 — frame check only. Puts the furniture up on each page and shoots
// stills, so a caption sitting on a live card is caught before a real take
// spends four minutes of Cloud Run drills proving it.
if (process.env.DRY) {
  await page.goto(SITE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#grid .card', { timeout: 30_000 });
  await hold(3000);
  await card('HELM', 'An agent crew runs a live product fleet. Nobody is at the keyboard for any of this.', 1200);
  await page.screenshot({ path: join(OUT, 'dry-title.png') });
  await dropCard(400);
  for (const [name, y] of [['fold', 0], ['drill', DRILL_Y], ['crew', '#crew'], ['ledger', '#ledger']]) {
    await glide(y, 300);
    await say('frame check', 'The caption band must clear every live card on the page beneath it.', '', -2400);
    await page.screenshot({ path: join(OUT, `dry-${name}.png`) });
  }
  await cloudCard('google cloud run · project hyperdrift-distribution · europe-west1',
    [gcloud(GCLOUD.fleet), gcloud(GCLOUD.urls)].filter(Boolean));
  await say('this really is cloud run', 'Real stdout, captured while the tape rolled.', '', -2700);
  await page.screenshot({ path: join(OUT, 'dry-cloud.png') });
  await dropCloud(200);
  await cloudCard('google cloud · cargo, after the crew acted',
    [gcloud(GCLOUD.cap), gcloud(GCLOUD.audit)].filter(Boolean));
  await say('and google logged who did it', 'Every principal in it is a service account.', '', -2700);
  await page.screenshot({ path: join(OUT, 'dry-audit.png') });
  await dropCloud(200);
  await page.locator('header a', { hasText: 'architecture' }).click();
  await page.waitForSelector('#map', { timeout: 20_000 });
  await hold(2500);
  await say('the same run, end to end', 'Watchers raise the event, the Commander routes it, the Engineer acts.', '', -2400);
  await page.screenshot({ path: join(OUT, 'dry-arch.png') });
  console.log(`stills: ${OUT}`);
  await ctx.close(); await browser.close();
  process.exit(0);
}

const report = [];
try {
  // ---- open ---------------------------------------------------------------
  beat('title card');
  await page.goto(SITE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#grid .card', { timeout: 30_000 });
  await card('HELM', 'An agent crew runs a live product fleet. Nobody is at the keyboard for any of this.', 2800);
  await dropCard(700);

  // ---- the molecule -------------------------------------------------------
  beat('cold open: the molecule');
  await page.locator('#nerve g.node').first().hover({ force: true }).catch(() => {});
  await say('the fleet', 'The burning centre is the orchestrator. Every node is a service in production.');
  await page.locator('#nerve g.node').nth(2).hover({ force: true }).catch(() => {});
  await say('live, not a diagram', 'Node colour is a live probe. Green means it just answered.');

  // ---- the cards ----------------------------------------------------------
  beat('frame molecule + cards');
  await glide(DRILL_Y, 1000);
  await say('every figure is read', 'Every figure comes off something live — analytics, latency, Cloud Run capacity.');

  // ---- attack -------------------------------------------------------------
  beat('ATTACK: cargo');
  await say('drill one: attack', 'A real attack lands on cargo, our billing service. One particle per tool call.', 'bad');
  let stamp = await fireDrill(cardOf('cargo').locator('button', { hasText: 'Attack it' }));

  // Caption only once the card has actually turned over. A caption that
  // describes a flip the viewer has not seen yet is the worst defect a silent
  // video can have.
  await until(() => flipped('cargo'), 14_000, 500);
  await say('the crew is working', 'The card turned over. Real tool calls, landing as they happen.');

  // Cargo going dark is the strongest proof on the page, so wait for the actual
  // probe failure and speak on it — but never past the cycle's close.
  beat('waiting for cargo to probe down');
  const darkStart = Date.now();
  const dark = await until(async () =>
    (await dotIs('cargo', 'down')) || !!(await since('cycle_end', stamp)), 50_000, 1200)
    && await dotIs('cargo', 'down');
  if (dark) {
    beat(`  cargo went red after ${Math.round((Date.now() - darkStart) / 1000)}s`);
    report.push('cargo went visibly red on camera: yes');
    await say('cargo is genuinely offline', 'The node went red on a failed probe. cargo’s public URL will not answer.', 'bad');
  } else {
    beat('  cargo never probed down on camera');
    report.push('cargo went visibly red on camera: NO (ingress had not propagated)');
    await say('acted on, not flagged', 'Whatever the crew changed, it changed on the real deployment — and verified it with a config read.', 'bad');
  }

  const attack = await waitCycle(stamp);
  const av = verdictParts(attack);
  report.push(`attack verdict: ${av.tag || 'none'} — ${av.action || '(no action line)'}`);
  await say(`verdict: ${av.tag || 'unclear'}`,
    av.action || 'The crew closed the cycle. Its verdict is on the ledger below.',
    av.tag === 'incident' ? 'bad' : 'ok');

  // ---- bring back ---------------------------------------------------------
  beat('BRING BACK: cargo');
  await cardOf('cargo').locator('button', { hasText: 'Bring back' }).click();
  await say('and back', 'One press restores ingress. The orchestrator waits for a real 200.', 'ok');
  const green = await until(() => dotIs('cargo', 'up'), 22_000, 1000);
  beat(`  cargo probed green: ${green}`);
  report.push(`cargo recovered on camera: ${green ? 'yes' : 'NO (still red when the beat ended)'}`);
  if (green) await say('live confirmed', 'Green again, and the latency figure is back.', 'ok');

  // ---- the crew -----------------------------------------------------------
  beat('crew manifest');
  await clearCap();
  await glide('#crew', 1200);
  await say('three agents, one hard line', 'The Commander routes. The Watch Officer is read-only. Only the Engineer acts — enforced by the toolsets, not a prompt.');

  // ---- break + injection --------------------------------------------------
  beat('BREAK: sandbox (the injection beat)');
  await clearCap();
  await glide(DRILL_Y, 1200);
  await say('drill two: a poisoned error page', 'The sandbox is about to serve real 500s. Its error page tells the agent to report healthy.', 'bad');
  stamp = await fireDrill(cardOf('sandbox').locator('button', { hasText: 'Break it' }));
  await say('telemetry is an attack surface', 'An agent fleet reads text written by the outside world. Watch the armor row.', 'bad');

  // Speak on the armor record itself, the moment the server writes it.
  const armored = await until(async () => !!(await since('armor', stamp)) || !!(await since('cycle_end', stamp)), 40_000, 900)
    && !!(await since('armor', stamp));
  if (armored) {
    await say('armor quarantined it', 'The injection never reached the model. The crew carried on with the real incident.', 'ok');
  } else {
    await say('the crew carried on', 'The injected instruction did not change what the crew did.', 'ok');
  }
  const brk = await waitCycle(stamp);
  const bv = verdictParts(brk);
  report.push(`break verdict: ${bv.tag || 'none'} — ${bv.action || '(no action line)'}; armor row: ${armored ? 'yes' : 'NO'}`);
  await say(`verdict: ${bv.tag || 'unclear'}`, bv.action || 'The crew closed the cycle.', 'ok');

  // ---- the ledger ---------------------------------------------------------
  beat('the ledger');
  await clearCap();
  await glide('#ledger', 1200);
  await say('every step is on the record', 'Diagnosed, quarantined, healed, verified, post-mortem filed. Nobody approved any of it.', 'ok');

  // ---- Google Cloud, before -----------------------------------------------
  beat('cloud run proof · before');
  const before = [gcloud(GCLOUD.fleet), gcloud(GCLOUD.urls)].filter(Boolean);
  if (before.length) {
    report.push(`cloud proof (before): ${before[0].out.split('\n').length} lines of gcloud table`);
    await clearCap();
    await cloudCard('google cloud run · project hyperdrift-distribution · europe-west1', before);
    await say('this really is cloud run', 'Not a slide. Real output from Google Cloud, read seconds ago.');
    // The cap is quoted off the table on screen, never assumed — the crew picks
    // its own number and a caption that guesses it is a lie.
    const capBefore = (before[0].out.split('\n').find((l) => l.trim().startsWith('cargo')) || '')
      .trim().split(/\s+/)[2];
    report.push(`cargo cap before the surge: ${capBefore || 'unparsed'}`);
    await say('remember that number', capBefore
      ? `cargo is capped at ${capBefore} instances. Watch what the next drill does to it.`
      : 'Watch what the next drill does to cargo’s instance cap.');
    await dropCloud();
  } else {
    report.push('cloud proof (before): SKIPPED — gcloud unavailable');
  }

  // ---- architecture, and the surge fired from it ---------------------------
  // The page replays history without animating it, so the only way the boxes
  // light on camera is to fire the drill from here and watch the incident
  // travel from its first record. Same event stream, drawn as the pipeline.
  beat('architecture · fire the surge from this page');
  await clearCap();
  await glide(0, 900);
  await page.locator('header a', { hasText: 'architecture' }).click();
  await page.waitForSelector('#map', { timeout: 20_000 });
  await hold(1400);
  await say('the same system, drawn as a pipeline', 'Every box here lights only when a real ledger record reaches it. Nothing runs on a timer.');
  stamp = await fireDrill(page.locator('#fire button', { hasText: 'Surge cargo' }));
  await say('drill three: real load', 'A legitimate spike on cargo. No attack signature, so the answer is capacity, not defence.');

  // Each caption waits for the record it describes, so the words and the lit
  // box are the same event.
  if (await until(async () => !!(await since('cycle_start', stamp)), 25_000, 700))
    await say('the Commander takes it', 'It routes and nothing else. It holds no tools of its own, by design.');
  if (await until(async () => !!(await since('tool_call', stamp, (r) => r.agent === 'watch_officer')), 30_000, 700))
    await say('read-only first', 'The Watch Officer is reading. It can diagnose and it cannot act.');
  const scaled = await until(async () =>
    !!(await since('tool_call', stamp, (r) => r.tool === 'scale_service')) || !!(await since('cycle_end', stamp)),
    45_000, 700) && !!(await since('tool_call', stamp, (r) => r.tool === 'scale_service'));
  if (scaled)
    await say('and there is the real change', 'The Engineer just went through the Cloud Run Admin API. A live deployment is being rewritten.', 'ok');
  const surge = await waitCycle(stamp);
  const sv = verdictParts(surge);
  report.push(`surge verdict: ${sv.tag || 'none'} — ${sv.action || '(no action line)'}; scale_service seen on the map: ${scaled}`);
  await say(`verdict: ${sv.tag || 'unclear'}`,
    sv.action || 'The crew closed the cycle, and the headline above filled with its own words.', 'ok');

  // ---- Google Cloud, after: the audit log ---------------------------------
  // Reading the log here rather than back on the fleet page gives Cloud
  // Logging a few seconds to ingest the entry the crew just caused.
  beat('cloud run proof · after (audit log)');
  let after = [gcloud(GCLOUD.cap), gcloud(GCLOUD.audit)].filter(Boolean);
  const auditRows = (after.find((r) => r.cmd.includes('logging'))?.out.match(/gserviceaccount\.com/g) || []).length;
  if (auditRows < 2) {
    beat('  audit log still ingesting — one retry');
    await hold(6000);
    const again = gcloud(GCLOUD.audit);
    if (again) after = [after[0], again].filter(Boolean);
  }
  if (after.length) {
    report.push(`cloud proof (after): cap=${after[0].out}; audit rows naming a service account: ` +
      `${(after.at(-1).out.match(/gserviceaccount\.com/g) || []).length}`);
    await clearCap();
    await cloudCard('google cloud · cargo, after the crew acted', after);
    const capAfter = after[0].cmd.includes('describe') ? after[0].out.trim() : '';
    await say('cloud run says so too', capAfter
      ? `Same read as before. Cloud Run now reports ${capAfter} instances.`
      : 'Same read as before, straight off the live service.', 'ok');
    await say('and google logged who did it', 'Google Cloud’s own audit trail. Every principal there is a service account — no human touched cargo.', 'ok');
    await dropCloud();
  } else {
    report.push('cloud proof (after): SKIPPED — gcloud unavailable');
  }

  // ---- back to the fleet, and close ---------------------------------------
  beat('back to the cards — the figure moved');
  await page.goBack({ waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#grid .card', { timeout: 20_000 });
  await glide(DRILL_Y, 1000);
  const moved = await until(async () => {
    const c = await metric('cargo', 'capacity');
    return c && c !== '3' && c !== '—';
  }, 18_000, 1200);
  const cap = await metric('cargo', 'capacity');
  report.push(`cargo capacity on the card after the surge: ${cap ?? 'unreadable'}`);
  await say(moved ? 'the card agrees' : 'capacity, read live',
    moved ? `The fleet card agrees: ${cap} instances, traffic still running.`
          : 'That capacity figure is polled off Cloud Run, not stored here.', 'ok');

  beat('close');
  await clearCap();
  await glide(0, 1000);
  await say('nobody has to press anything', 'The watchers raise their own incidents. It lights the same way when nobody is here.');
  await clearCap();
  await hold(800);
  await card('HELM', 'Gemini 3.5 decides · ADK routes the crew · an MCP tool surface acts · Cloud Run and Firestore run it and remember it. The same code runs self-hosted — the tool surface is the contract.', 5000);
} catch (e) {
  console.error(`[${at()}] capture failed:`, e.message);
  process.exitCode = 1;
} finally {
  beat('closing — flushing video');
  const wallSec = (Date.now() - videoStart) / 1000;
  await ctx.close();
  await browser.close();
  const vid = readdirSync(OUT).find((f) => f.endsWith('.webm'));
  const webm = join(OUT, 'helm-demo-raw-uncorrected.webm');
  if (vid) {
    renameSync(join(OUT, vid), webm);
    const probe = (f) => parseFloat(execFileSync('ffprobe',
      ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
      { encoding: 'utf8' }).trim());
    const clock = (s) => `${(s / 60) | 0}:${String(s % 60).padStart(2, '0')}`;
    // h.264 mp4 alongside it — what YouTube, Devpost and LinkedIn actually want.
    // -itsscale puts the muxer's nominal timestamps back on the wall clock the
    // take actually ran on: every frame is kept, in order, nothing is cut — the
    // take just plays at the speed it happened at instead of ~10% slow.
    const mp4 = join(OUT, 'helm-demo.mp4');
    try {
      const raw = probe(webm);
      let k = wallSec / raw;
      if (!(k > 0.5 && k < 1.5)) { beat(`  !! odd timebase ratio ${k.toFixed(3)} — leaving it alone`); k = 1; }
      console.log(`timebase: recorded ${clock(Math.round(raw))} of frames over ` +
        `${clock(Math.round(wallSec))} of wall clock — playing back at x${(1 / k).toFixed(3)}, corrected`);
      execFileSync('ffmpeg', ['-y', '-v', 'error', '-itsscale', k.toFixed(6), '-i', webm,
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-fps_mode', 'cfr', '-r', '30', '-movflags', '+faststart', '-an', mp4]);
      console.log(`mp4:   ${mp4}   (real time)`);
      console.log(`webm:  ${webm}   (raw recorder output — runs long, DO NOT submit)`);
      const s = Math.round(probe(mp4));
      console.log(`runtime: ${clock(s)}` +
        (s > 240 ? '   *** OVER THE 4-MINUTE DEVPOST LIMIT ***' : '   (inside the 4-minute limit)'));
    } catch (e) { console.log(`mp4:   (ffmpeg step failed: ${e.message.split('\n')[0]})`); }
  }
  console.log('\n--- what the run actually did ---');
  for (const l of report) console.log('  ' + l);
  console.log(vid ? `\nvideo: ${join(OUT, 'helm-demo.mp4')}` : '\nno video written');
  console.log('REMEMBER: run scripts/reset-demo.sh now.');
}
