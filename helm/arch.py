"""The live architecture diagram — the same pipeline as the static SVG, but
every stage lights when a real ledger record passes through it.

Served by web.py at /architecture. One export: ARCH_PAGE.
"""

ARCH_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Helm — live architecture</title>
<style>
:root {
  --sea:#0a1015; --panel:#101a21; --raise:#16232c; --line:#1f2f3a;
  --ink:#e8e4d8; --dim:#7d8894; --gold:#d8a03d; --ok:#5fae6e; --alert:#e0532f;
  --step:clamp(.9rem,2vw,1.6rem);
}
* { box-sizing:border-box; }
html { background:var(--sea); color-scheme:dark; }
body { margin:0 auto; max-width:84rem; padding:2.2rem var(--step) 5rem; color:var(--ink);
       font:14px/1.6 ui-monospace,'SF Mono',Menlo,monospace; overflow-x:hidden; }

header { display:flex; align-items:baseline; gap:1rem; flex-wrap:wrap; }
h1 { font-size:clamp(1.3rem,3.2vw,1.9rem); margin:0; letter-spacing:.16em; font-weight:700; }
h1 b { color:var(--gold); font-weight:700; }
header p { margin:0; color:var(--dim); max-width:44rem; }
header a { color:var(--gold); margin-left:auto; font-size:.8rem; }
header a:hover { color:var(--ink); }

h2 { font-size:.72rem; text-transform:uppercase; letter-spacing:.18em;
     color:var(--dim); font-weight:400; margin:2.2rem 0 .8rem; }
h2 span { color:var(--gold); }

/* ---- the pipeline ---- */
#map { position:relative; display:grid; gap:1.1rem 2.2rem; margin-top:1.4rem;
       align-items:center; grid-template-columns:1.1fr .95fr 1.05fr .95fr 1fr 1fr;
       grid-template-areas:
         "src cmd watch armor mcp run"
         "src cmd eng   armor mcp gh"
         "src cmd .     armor mcp apps"
         "led led led   led   led led"; }
#n-src{grid-area:src} #n-cmd{grid-area:cmd} #n-watch{grid-area:watch}
#n-eng{grid-area:eng} #n-armor{grid-area:armor} #n-mcp{grid-area:mcp}
#n-run{grid-area:run} #n-gh{grid-area:gh} #n-apps{grid-area:apps} #n-led{grid-area:led}

#wires { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }
#wires path { fill:none; stroke:#2b4150; stroke-width:1.4;
              transition:stroke .3s,stroke-width .3s; }
#wires path[data-bus] { stroke:#1c2b35; stroke-dasharray:3 6; }
#wires path[data-lit] { stroke:var(--gold); stroke-width:2.2; }
#wires circle { fill:var(--gold); }

#map > section { position:relative; z-index:1; border:1px solid var(--line);
  background:linear-gradient(160deg,var(--raise),var(--panel)); padding:.75rem .85rem;
  transition:border-color .35s,box-shadow .35s,background .35s; }
#map > section[data-lit] { border-color:var(--gold); background:#1a1608;
  box-shadow:0 0 0 1px rgba(216,160,61,.2); }
#map > section[data-lit="alert"] { border-color:var(--alert); background:#1d0f0c;
  box-shadow:0 0 0 1px rgba(224,83,47,.28); }
#map h3 { margin:0; font-size:.8rem; letter-spacing:.06em; color:var(--gold); font-weight:400; }
#map h3 em { color:var(--dim); font-style:normal; font-size:.66rem; letter-spacing:.14em;
             text-transform:uppercase; margin-left:.45rem; }
#map p { margin:.35rem 0 0; color:var(--dim); font-size:.72rem; line-height:1.5; }
#map code { color:var(--ink); }
#map ul { margin:.4rem 0 0; padding:0; list-style:none; color:var(--dim); font-size:.7rem; }
#map li { padding:.05rem 0; }
#map li::before { content:'· '; color:#3d5262; }
#n-armor { border-style:dashed; }
#n-led { text-align:center; }

#fire { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.7rem; }
button { font:inherit; font-size:.74rem; border:1px solid var(--alert); background:transparent;
         color:var(--alert); padding:.3rem .6rem; cursor:pointer; letter-spacing:.03em;
         transition:background .2s,color .2s; }
button:hover { background:var(--alert); color:var(--sea); }
button[disabled] { border-color:var(--line); color:var(--dim); cursor:wait; background:transparent; }
#said { min-height:1.2em; color:var(--gold); font-size:.7rem; }

#verdict { border:1px solid var(--line); background:var(--panel); padding:.7rem .9rem;
           margin:1.6rem 0 0; white-space:pre-wrap; color:var(--dim); font-size:.8rem; }
#verdict[data-v] { color:var(--ok); border-color:#26402c; }

#stream { list-style:none; margin:.2rem 0 0; padding:0; max-height:24rem; overflow-y:auto;
          border:1px solid var(--line); background:var(--panel); }
#stream li { padding:.35rem .8rem; border-bottom:1px solid var(--line); white-space:pre-wrap;
             word-break:break-word; font-size:.78rem; color:var(--dim); }
#stream time { color:#5c6773; margin-right:.7rem; }
#stream li[data-kind="event"] { color:var(--gold); }
#stream li[data-kind="armor"] { color:var(--alert); }
#stream li[data-kind="cycle_end"] { color:var(--ok); }
#conn { color:var(--dim); font-size:.7rem; letter-spacing:.1em; text-transform:uppercase; }
#conn[data-on] { color:var(--ok); }
footer { color:var(--dim); font-size:.76rem; margin-top:2.4rem; }

@media (max-width:1080px) {
  #map { grid-template-columns:1fr 1fr;
         grid-template-areas:"src cmd" "watch eng" "armor mcp" "run gh" "apps apps" "led led"; }
}
@media (max-width:620px) {
  #map { grid-template-columns:1fr;
         grid-template-areas:"src" "cmd" "watch" "eng" "armor" "mcp" "run" "gh" "apps" "led"; }
}
@media (prefers-reduced-motion:reduce) {
  #map > section, #wires path { transition:none; }
}
</style></head><body>

<header>
  <h1>HELM · <b>ARCHITECTURE</b></h1>
  <p>The live version of the diagram: each box lights only when a real ledger
     record passes through it. Press a drill and watch one incident travel.</p>
  <a href="/">← the fleet</a>
</header>

<section id="map">
  <svg id="wires" aria-hidden="true">
    <defs><marker id="tip" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6"
      markerHeight="6" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#2b4150"/></marker></defs>
    <g id="paths"></g><g id="pulses"></g>
  </svg>

  <section id="n-src" data-role="source">
    <h3>Event sources</h3>
    <ul><li>uptime watcher</li><li>PostHog signal watcher</li>
        <li>/webhook</li><li>drill buttons</li></ul>
    <div id="fire">
      <button type="button" data-path="/drill">Break sandbox</button>
      <button type="button" data-path="/drill/attack">Attack cargo</button>
      <button type="button" data-path="/drill/surge">Surge cargo</button>
    </div>
    <p id="said"></p>
  </section>

  <section id="n-cmd" data-role="commander">
    <h3>helm <em>Commander</em></h3>
    <p>Gemini 3.5. Routes each event: diagnose first, act only on a confirmed
       diagnosis. Holds no tools by design.</p>
  </section>

  <section id="n-watch" data-role="agent">
    <h3>watch_officer <em>read-only</em></h3>
    <ul><li>get_recent_actions</li><li>get_fleet_status</li>
        <li>get_app_detail</li><li>get_app_signals</li></ul>
  </section>

  <section id="n-eng" data-role="agent">
    <h3>engineer <em>act-scoped</em></h3>
    <ul><li>heal_service</li><li>take_offline · bring_online</li>
        <li>scale_service · get_service_config</li><li>file_github_issue</li></ul>
  </section>

  <section id="n-armor" data-role="gate">
    <h3>armor screen</h3>
    <p>The gate on results coming back in: instruction-shaped text in a probe
       result is quarantined before the model reads it.</p>
  </section>

  <section id="n-mcp" data-role="surface">
    <h3>Fleet MCP</h3>
    <p>The tool surface — a standalone MCP server. A per-agent
       <code>tool_filter</code> enforces the two identities by construction,
       not by prompt.</p>
  </section>

  <section id="n-run" data-role="effect">
    <h3>Cloud Run Admin API</h3>
    <p>Ingress cut · scale. Allowlisted to the drill assets.</p>
  </section>

  <section id="n-gh" data-role="effect">
    <h3>GitHub issues</h3>
    <p>Post-mortems and escalations, filed for real.</p>
  </section>

  <section id="n-apps" data-role="effect">
    <h3>The live fleet</h3>
    <p>revela · nextrole · intel · web3-capital · cargo · sandbox</p>
  </section>

  <section id="n-led" data-role="ledger">
    <h3>Firestore ledger</h3>
    <p>Every event, tool call, quarantine and verdict — and the feed this page reads.</p>
  </section>
</section>

<p id="verdict">No cycle has closed yet. Press a drill above.</p>

<h2>Live ledger — <span id="conn">connecting</span></h2>
<ol id="stream" reversed></ol>

<footer>Gemini 3.5 decides · ADK routes the crew · an MCP tool surface acts ·
Cloud Run and Firestore run and remember it.</footer>

<script>
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const SVGNS = 'http://www.w3.org/2000/svg';
const map = document.getElementById('map');
const wires = document.getElementById('wires');
const stream = document.getElementById('stream');

const LINKS = [['src','cmd'],['cmd','watch'],['cmd','eng'],['watch','armor'],
               ['eng','armor'],['armor','mcp'],['mcp','run'],['mcp','gh'],['mcp','apps']];
const BUS = ['src','cmd','watch','eng','armor','mcp'];
const EDGES = {};

function makeEdge(a, b, bus){
  const p = document.createElementNS(SVGNS,'path');
  if(bus) p.dataset.bus = '1'; else p.setAttribute('marker-end','url(#tip)');
  document.getElementById('paths').appendChild(p);
  EDGES[a+'>'+b] = {p:p, a:a, b:b};
}
LINKS.forEach(function(l){ makeEdge(l[0], l[1], false); });
BUS.forEach(function(n){ makeEdge(n, 'led', true); });

function box(id){
  const e = document.getElementById('n-'+id); if(!e) return null;
  const r = e.getBoundingClientRect(), m = map.getBoundingClientRect();
  return {l:r.left-m.left, t:r.top-m.top, r:r.right-m.left, b:r.bottom-m.top,
          cx:r.left-m.left+r.width/2, cy:r.top-m.top+r.height/2};
}
function shape(a, b, bus){
  if(bus && b.t > a.b+4) return 'M'+a.cx+','+a.b+'L'+a.cx+','+b.t;
  if(b.l > a.r+4){
    const k = Math.max(16,(b.l-a.r)*0.45);
    return 'M'+a.r+','+a.cy+'C'+(a.r+k)+','+a.cy+' '+(b.l-k)+','+b.cy+' '+b.l+','+b.cy;
  }
  if(b.t > a.b+4){
    const k = Math.max(12,(b.t-a.b)*0.5);
    return 'M'+a.cx+','+a.b+'C'+a.cx+','+(a.b+k)+' '+b.cx+','+(b.t-k)+' '+b.cx+','+b.t;
  }
  return 'M'+a.cx+','+a.cy+'L'+b.cx+','+b.cy;
}
let pending = false;
function layout(){
  pending = false;
  const m = map.getBoundingClientRect();
  wires.setAttribute('viewBox','0 0 '+Math.round(m.width)+' '+Math.round(m.height));
  for(const k in EDGES){
    const e = EDGES[k], a = box(e.a), b = box(e.b);
    if(a && b) e.p.setAttribute('d', shape(a, b, e.p.dataset.bus));
  }
}
function relayout(){ if(!pending){ pending = true; requestAnimationFrame(layout); } }
relayout();
addEventListener('resize', relayout);
if(window.ResizeObserver) new ResizeObserver(relayout).observe(map);

const TIMERS = {};
function light(id, alert){
  const n = document.getElementById('n-'+id); if(!n) return;
  n.dataset.lit = alert ? 'alert' : 'on';
  clearTimeout(TIMERS[id]);
  TIMERS[id] = setTimeout(function(){ delete n.dataset.lit; }, 1500);
}
function pulse(p){
  const c = document.createElementNS(SVGNS,'circle');
  c.setAttribute('r', 3.4);
  document.getElementById('pulses').appendChild(c);
  const L = p.getTotalLength(), t0 = performance.now(), dur = 700;
  (function step(now){
    const k = Math.min(1,(now-t0)/dur), pt = p.getPointAtLength(L*k);
    c.setAttribute('cx', pt.x); c.setAttribute('cy', pt.y);
    c.setAttribute('opacity', 1-k*0.5);
    if(k < 1) requestAnimationFrame(step); else c.remove();
  })(t0);
}
function fireEdge(a, b, delay){
  const e = EDGES[a+'>'+b]; if(!e) return;
  setTimeout(function(){
    e.p.dataset.lit = 'on';
    clearTimeout(e.t); e.t = setTimeout(function(){ delete e.p.dataset.lit; }, 1500);
    if(!REDUCED) pulse(e.p);
  }, REDUCED ? 0 : (delay || 0));
}

const AGENT = {watch_officer:'watch', engineer:'eng', helm:'cmd'};
const RUN_TOOLS = {take_offline:1, bring_online:1, scale_service:1, get_service_config:1};
const APP_TOOLS = {get_fleet_status:1, get_app_detail:1, get_app_signals:1, heal_service:1};

function verdict(text){
  const t = String(text || '').trim(); if(!t) return;
  const el = document.getElementById('verdict');
  const m = t.match(/VERDICT:\s*([\w-]+)/);
  if(m) el.dataset.v = m[1]; else delete el.dataset.v;
  el.textContent = t;
}

function animate(r){
  const k = r.kind;
  light('led');
  if(k === 'event'){ light('src'); fireEdge('src','led',120); }
  else if(k === 'cycle_start'){ light('cmd'); fireEdge('src','cmd'); fireEdge('cmd','led',320); }
  else if(k === 'tool_call'){
    const who = AGENT[r.agent];
    if(who) light(who);
    if(who === 'cmd'){
      const to = AGENT[(r.args || {}).agent_name];
      if(to && to !== 'cmd') fireEdge('cmd', to);
    } else if(who){
      light('mcp'); fireEdge(who,'armor'); fireEdge('armor','mcp',180);
      if(RUN_TOOLS[r.tool]){ light('run'); fireEdge('mcp','run',360); }
      if(r.tool === 'file_github_issue'){ light('gh'); fireEdge('mcp','gh',360); }
      if(APP_TOOLS[r.tool]){ light('apps'); fireEdge('mcp','apps',360); }
    }
    fireEdge(who || 'cmd','led',520);
  }
  else if(k === 'armor'){ light('armor', true); fireEdge('armor','led',200); }
  else if(k === 'cycle_end'){ light('cmd'); verdict(r.verdict); fireEdge('cmd','led',120); }
  else if(k === 'cycle_retry'){ light('cmd'); fireEdge('cmd','led',120); }
}

function render(r, live){
  const li = document.createElement('li');
  li.dataset.kind = r.kind || '';
  const ev = r.event || {};
  let txt = r.kind || 'record';
  if(r.kind === 'event') txt = 'EVENT  ' + (r.event_desc || ((ev.app||'?') + ' ' + (ev.kind||'')));
  else if(r.kind === 'cycle_start') txt = 'CYCLE  ' + (ev.kind||'') + ' · ' + (ev.app||'');
  else if(r.kind === 'tool_call') txt = 'TOOL   ' + (r.agent||'') + ' → ' + (r.tool||'');
  else if(r.kind === 'armor') txt = 'ARMOR  quarantined: "' + String(r.quarantined||'').slice(0,90) + '"';
  else if(r.kind === 'control') txt = 'CTRL   ' + (r.app||'') + ' ' + (r.pct||0) + '% ' + (r.step||'');
  else if(r.kind === 'cycle_end') txt = String(r.verdict||'done').trim();
  else if(r.kind === 'cycle_retry') txt = 'RETRY  ' + (r.reason||'');
  li.innerHTML = '<time>' + String(r.ts||'').slice(11,19) + '</time>' + txt.replace(/</g,'&lt;');
  stream.prepend(li);
  while(stream.children.length > 80) stream.lastChild.remove();
  if(live) animate(r);
}

const said = document.getElementById('said');
document.querySelectorAll('#fire button').forEach(function(b){
  b.addEventListener('click', async function(){
    b.disabled = true;
    setTimeout(function(){ b.disabled = false; }, 60000);
    said.textContent = 'sent — ' + b.textContent.toLowerCase();
    try {
      const res = await fetch(b.dataset.path, {method:'POST'});
      const j = await res.json().catch(function(){ return {}; });
      said.textContent = j.queued === false
        ? (j.reason || 'stood down')
        : 'event raised — watch it travel';
    } catch(e){ said.textContent = 'the bridge did not answer — try again'; }
  });
});

const conn = document.getElementById('conn');
fetch('/recent').then(function(r){ return r.json(); })
  .then(function(rows){ rows.forEach(function(r){ render(r, false); }); })
  .catch(function(){});
const es = new EventSource('/stream');
es.onopen = function(){ conn.dataset.on = '1'; conn.textContent = 'live'; };
es.onerror = function(){ delete conn.dataset.on; conn.textContent = 'reconnecting'; };
es.onmessage = function(e){
  let r; try { r = JSON.parse(e.data); } catch(err){ return; }
  if(r && typeof r === 'object') render(r, true);
};
</script></body></html>"""
