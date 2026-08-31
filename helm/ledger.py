"""One ledger store, shared by both views.

The fleet page and the architecture page were each opening their own feed and
each replaying history from scratch, so moving between them meant a blank list,
a refetch, and a reconnect — the crew appeared to stop working mid-cycle.

The store owns the records, the connection, and what survives a navigation. A
page arrives already knowing what the last one saw, then reconciles with the
server. Views subscribe and render; they no longer fetch anything themselves.
"""

from __future__ import annotations

LEDGER_JS = """/* Helm — the shared ledger store. One feed, however many views. */
(function () {
  var KEY = 'helm.ledger', CAP = 120;
  var subs = [], conns = [], seen = {}, records = [];
  var connected = false, hydrated = false, pending = [];

  /* Records carry a monotonic seq; fall back to a composite for anything
     written before that existed, so a replay can never double-render. */
  function key(r) {
    if (r.seq !== undefined && r.seq !== null) return 's' + r.seq;
    return [r.ts, r.kind, r.tool, r.step, r.app, r.verdict].join('|');
  }

  function remember() {
    try { sessionStorage.setItem(KEY, JSON.stringify(records.slice(-CAP))); }
    catch (e) { /* private mode, quota, disabled storage — the feed still works */ }
  }

  function add(r, live) {
    var k = key(r);
    if (seen[k]) return false;
    seen[k] = 1;
    records.push(r);
    /* Forget the key with the record it belongs to, or a page left open on a
       busy fleet grows an index it never reads again. */
    if (records.length > CAP) delete seen[key(records.shift())];
    for (var i = 0; i < subs.length; i++) {
      try { subs[i](r, live); } catch (e) { }
    }
    return true;
  }

  function announce() {
    for (var i = 0; i < conns.length; i++) {
      try { conns[i](connected); } catch (e) { }
    }
  }

  window.Ledger = {
    /* fn(record, live) — live is false while replaying what we already knew,
       which is how a view knows not to re-animate history. */
    subscribe: function (fn) {
      subs.push(fn);
      for (var i = 0; i < records.length; i++) fn(records[i], false);
    },
    onConnection: function (fn) { conns.push(fn); fn(connected); },
    records: function () { return records.slice(); }
  };

  /* 1. Paint instantly from whatever the previous page knew. */
  try {
    var cached = JSON.parse(sessionStorage.getItem(KEY) || '[]');
    for (var i = 0; i < cached.length; i++) {
      var k = key(cached[i]);
      if (!seen[k]) { seen[k] = 1; records.push(cached[i]); }
    }
  } catch (e) { }

  /* 2. Open the feed first and hold what arrives, so nothing slips through the
        gap between history landing and the connection opening. */
  var es = new EventSource('/stream');
  es.onopen = function () { connected = true; announce(); };
  es.onerror = function () { connected = false; announce(); };
  es.onmessage = function (e) {
    var r;
    try { r = JSON.parse(e.data); } catch (err) { return; }
    if (!hydrated) { pending.push(r); return; }
    if (add(r, true)) remember();
  };

  /* 3. Reconcile with the server, then release what the feed was holding. */
  fetch('/recent')
    .then(function (r) { return r.json(); })
    .then(function (rows) { for (var i = 0; i < rows.length; i++) add(rows[i], false); })
    .catch(function () { })
    .then(function () {
      hydrated = true;
      for (var i = 0; i < pending.length; i++) add(pending[i], true);
      pending = [];
      remember();
    });

  window.addEventListener('pagehide', remember);
})();
"""
