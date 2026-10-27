/* MMM dashboard, static HTML twin. Vanilla JS, inline SVG, no dependencies.
   Data: the JSON block #dashboard-data, a copy of reports/exports/*.csv. */
(function () {
  'use strict';

  var D = JSON.parse(document.getElementById('dashboard-data').textContent);
  var SVGNS = 'http://www.w3.org/2000/svg';
  var state = { scenario: 'same_total', hidden: {} };
  var CHAR = 6.6; // average glyph width of 12px system sans, for label fitting

  // ---------------------------------------------------------------- helpers
  function s(tag, attrs, parent, text) {
    var n = document.createElementNS(SVGNS, tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text !== undefined) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  }
  function uniq(list) { return list.filter(function (v, i) { return list.indexOf(v) === i; }); }
  function money(x) { return Math.round(x).toLocaleString('en-US'); }
  function compact(x) {
    var a = Math.abs(x);
    if (a >= 1e6) return (x / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, '') + 'M';
    if (a >= 1e3) return (x / 1e3).toFixed(a >= 1e4 ? 0 : 1).replace(/\.0$/, '') + 'k';
    return String(Math.round(x * 100) / 100);
  }
  function pct(f, d) { return (100 * f).toFixed(d === undefined ? 1 : d) + '%'; }
  function ratio(x) { return x.toFixed(2); }
  function signedPct(v) { return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'; }
  function esc(t) {
    return String(t).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function fit(text, px) {
    var max = Math.floor(px / CHAR);
    return text.length <= max ? text : text.slice(0, Math.max(1, max - 1)) + '…';
  }
  function linear(d0, d1, r0, r1) {
    var f = function (x) { return r0 + (x - d0) / (d1 - d0 || 1) * (r1 - r0); };
    f.domain = [d0, d1];
    return f;
  }
  function logScale(d0, d1, r0, r1) {
    var a = Math.log(d0), b = Math.log(d1);
    return function (x) { return r0 + (Math.log(Math.max(x, d0 / 10)) - a) / (b - a) * (r1 - r0); };
  }
  function niceStep(range, n) {
    var raw = range / Math.max(n, 1), p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  }
  function ticks(lo, hi, n) {
    var step = niceStep(hi - lo, n), out = [], v = Math.ceil(lo / step) * step;
    for (; v <= hi + step * 1e-9; v += step) out.push(Math.round(v / step) * step);
    return out;
  }
  function niceMax(v, n) { var st = niceStep(v, n); return Math.ceil(v / st) * st; }
  // A value axis from 0: one step for the ticks and the top, so the top is always a tick.
  function axisFrom0(v, n) {
    var st = niceStep(v, n), top = Math.ceil(v / st) * st, out = [];
    for (var t = 0; t <= top + st * 1e-9; t += st) out.push(Math.round(t / st) * st);
    return { max: top, ticks: out };
  }
  function size(el) { return { w: Math.max(260, el.clientWidth), h: el.clientHeight }; }
  function svgFor(el, w, h) {
    el.textContent = '';
    return s('svg', { viewBox: '0 0 ' + w + ' ' + h, width: w, height: h,
      'aria-hidden': 'false', focusable: 'false' }, el);
  }
  function fill(v) { return 'fill:' + v; }
  function stroke(v, w) { return 'fill:none;stroke:' + v + ';stroke-width:' + (w || 2); }

  function yAxis(g, y, tks, x0, x1, fmt) {
    var ax = s('g', { 'class': 'ax' }, g);
    tks.forEach(function (t) {
      s('line', { x1: x0, x2: x1, y1: y(t), y2: y(t), 'class': 'grid-l' }, g);
      s('text', { x: x0 - 6, y: y(t) + 4, 'text-anchor': 'end' }, ax, fmt(t));
    });
  }
  function xAxis(g, x, tks, y0, fmt, title, x1) {
    var ax = s('g', { 'class': 'ax' }, g);
    s('line', { x1: x(tks[0]), x2: x1 !== undefined ? x1 : x(tks[tks.length - 1]), y1: y0, y2: y0 }, ax);
    tks.forEach(function (t, i) {
      var anchor = i === 0 ? 'start' : 'middle';
      s('text', { x: x(t), y: y0 + 16, 'text-anchor': anchor }, ax, fmt(t));
    });
    if (title) s('text', { x: x1 !== undefined ? x1 : x(tks[tks.length - 1]), y: y0 + 32, 'text-anchor': 'end' }, ax, title);
  }

  // ---------------------------------------------------------------- tooltip
  var tip = document.getElementById('tip');
  function showTip(html, cx, cy) {
    tip.innerHTML = html;
    tip.hidden = false;
    var w = tip.offsetWidth, h = tip.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
    var left = cx + 14, top = cy + 14;
    if (left + w > vw - 8) left = Math.max(8, cx - w - 14);
    if (top + h > vh - 8) top = Math.max(8, cy - h - 14);
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function hideTip() { tip.hidden = true; }
  function rows(pairs) {
    return pairs.map(function (p) {
      return '<div class="row"><span>' + esc(p[0]) + '</span><span>' + esc(p[1]) + '</span></div>';
    }).join('');
  }

  /* One focus target per chart. Pointer: nearest item. Keyboard: arrows step through items.
     items: [{x, y, html}] in SVG coordinates; axis 'x' or 'y' picks the nearest by that axis. */
  function interact(svg, box, items, opts) {
    if (!items.length) return;
    var cross = null, idx = -1;
    if (opts.cross) cross = s('line', { 'class': 'cross', y1: box.y, y2: box.y + box.h, x1: -10, x2: -10, visibility: 'hidden' }, svg);
    var mark = s('circle', { r: 6, style: 'fill:none;stroke:var(--ink);stroke-width:2', visibility: 'hidden' }, svg);
    var hit = s('rect', { x: box.x, y: box.y, width: Math.max(1, box.w), height: Math.max(1, box.h),
      'class': 'hit', tabindex: 0, role: 'img', 'aria-label': opts.label }, svg);
    function place(i, cx, cy) {
      idx = i;
      var it = items[i];
      if (cross) { cross.setAttribute('x1', it.x); cross.setAttribute('x2', it.x); cross.setAttribute('visibility', 'visible'); }
      if (opts.dot !== false) { mark.setAttribute('cx', it.x); mark.setAttribute('cy', it.y); mark.setAttribute('visibility', 'visible'); }
      if (cx === undefined) {
        var r = svg.getBoundingClientRect();
        cx = r.left + it.x; cy = r.top + it.y;
      }
      showTip(it.html, cx, cy);
    }
    function nearest(px, py) {
      var best = 0, bd = Infinity;
      items.forEach(function (it, i) {
        var d = opts.axis === 'y' ? Math.abs(it.y - py) : opts.axis === 'x' ? Math.abs(it.x - px)
          : Math.hypot(it.x - px, it.y - py);
        if (d < bd) { bd = d; best = i; }
      });
      return best;
    }
    function clear() {
      hideTip();
      if (cross) cross.setAttribute('visibility', 'hidden');
      mark.setAttribute('visibility', 'hidden');
    }
    hit.addEventListener('pointermove', function (e) {
      var r = svg.getBoundingClientRect();
      place(nearest(e.clientX - r.left, e.clientY - r.top), e.clientX, e.clientY);
    });
    hit.addEventListener('pointerleave', clear);
    hit.addEventListener('blur', clear);
    hit.addEventListener('focus', function () { place(idx < 0 ? 0 : idx); });
    hit.addEventListener('keydown', function (e) {
      var k = e.key, n = items.length, i = idx < 0 ? 0 : idx;
      if (k === 'ArrowRight' || k === 'ArrowDown') i = Math.min(n - 1, i + 1);
      else if (k === 'ArrowLeft' || k === 'ArrowUp') i = Math.max(0, i - 1);
      else if (k === 'Home') i = 0;
      else if (k === 'End') i = n - 1;
      else if (k === 'Escape') { clear(); return; }
      else return;
      e.preventDefault();
      place(i);
    });
  }

  function legend(svg, x, y, entries) {
    var g = s('g', {}, svg), cx = x;
    entries.forEach(function (e) {
      if (e.kind === 'line') s('line', { x1: cx, x2: cx + 16, y1: y - 4, y2: y - 4, style: stroke(e.color, e.width || 2) + (e.dash ? ';stroke-dasharray:' + e.dash : '') }, g);
      else if (e.kind === 'hollow') s('circle', { cx: cx + 6, cy: y - 4, r: 5, style: 'fill:var(--surface);stroke:' + e.color + ';stroke-width:2' }, g);
      else if (e.kind === 'dot') s('circle', { cx: cx + 6, cy: y - 4, r: 5, style: fill(e.color) }, g);
      else s('rect', { x: cx, y: y - 10, width: 12, height: 12, style: fill(e.color) }, g);
      var w = e.kind === 'line' ? 22 : 18;
      s('text', { x: cx + w, y: y, 'class': 'lbl-ink' }, g, e.label);
      cx += w + e.label.length * CHAR + 18;
    });
    return g;
  }

  // ---------------------------------------------------------------- page 1
  var ALLOC = D.recommendation_allocation;
  var GAIN = {};
  D.recommendation_gain.forEach(function (g) { GAIN[g.scenario] = g; });

  function drawSpend(el) {
    var rowsS = ALLOC.filter(function (r) { return r.scenario === state.scenario; });
    var z = size(el), W = z.w, H = z.h, narrow = W < 480;
    var m = { l: narrow ? 84 : 104, r: 16, t: 34, b: 46 };
    var vmax = 0;
    ALLOC.forEach(function (r) { vmax = Math.max(vmax, r.current_spend, r.recommended_spend); });
    var x = linear(0, niceMax(vmax, 4), m.l, W - m.r);
    var svg = svgFor(el, W, H), g = s('g', {}, svg);
    var tks = ticks(0, x.domain[1], narrow ? 3 : 5);
    tks.forEach(function (t) { s('line', { x1: x(t), x2: x(t), y1: m.t, y2: H - m.b, 'class': 'grid-l' }, g); });
    xAxis(g, x, tks, H - m.b, compact, 'Weekly spend, dataset money units', W - m.r);
    legend(svg, m.l, 16, [{ label: 'Current', color: 'var(--ink-2)' }, { label: 'Recommended', color: 'var(--hl)' }]);
    var band = (H - m.t - m.b) / rowsS.length, th = Math.min(12, band * 0.28);
    var items = [];
    rowsS.forEach(function (r, i) {
      var y0 = m.t + i * band + band / 2 - th - 1;
      s('text', { x: m.l - 8, y: y0 + th + 1, 'text-anchor': 'end', 'class': 'lbl-strong', 'dominant-baseline': 'middle' }, g, fit(r.channel, m.l - 10));
      if (r.held_by_rule) s('text', { x: m.l - 8, y: y0 + th + 16, 'text-anchor': 'end', 'class': 'lbl' }, g, 'held by rule');
      [[r.current_spend, 'var(--ink-2)', y0], [r.recommended_spend, 'var(--hl)', y0 + th + 2]].forEach(function (b, j) {
        var w = Math.max(1, x(b[0]) - m.l);
        s('rect', { x: m.l, y: b[2], width: w, height: th, style: fill(b[1]) }, g);
        var label = j === 0 ? money(b[0]) : money(b[0]) + ' (' + signedPct(r.delta_pct) + ')';
        var lx = m.l + w + 4, inside = lx + label.length * CHAR > W - 2;
        s('text', { x: inside ? m.l + w - 4 : lx, y: b[2] + th - 2, 'text-anchor': inside ? 'end' : 'start',
          style: inside ? 'font:12px var(--font);fill:' + (j === 0 ? 'var(--surface)' : 'var(--on-hl)') : '',
          'class': inside ? '' : 'lbl-ink' }, g, label);
      });
      items.push({ x: x(Math.max(r.current_spend, r.recommended_spend)), y: y0 + th, html:
        '<b>' + esc(r.channel) + '</b>' + rows([['Current', money(r.current_spend)],
          ['Recommended', money(r.recommended_spend)], ['Change', signedPct(r.delta_pct)],
          ['Rule', r.held_by_rule ? 'held by rule' : 'free to move']]) });
    });
    interact(svg, { x: m.l, y: m.t, w: W - m.l - m.r, h: H - m.t - m.b }, items,
      { axis: 'y', dot: false, label: 'Weekly spend per channel. Use the arrow keys to read each channel.' });
  }

  function drawMroas(el) {
    var rowsS = ALLOC.filter(function (r) { return r.scenario === state.scenario; });
    var z = size(el), W = z.w, H = z.h, narrow = W < 480;
    var m = { l: narrow ? 84 : 104, r: narrow ? 44 : 56, t: 34, b: 46 };
    var be = GAIN[state.scenario].breakeven_roas;
    var x = logScale(0.05, 60, m.l, W - m.r);
    var svg = svgFor(el, W, H), g = s('g', {}, svg);
    var tks = narrow ? [0.1, 1, 10] : [0.1, 0.3, 1, 3, 10, 30];
    tks.forEach(function (t) { s('line', { x1: x(t), x2: x(t), y1: m.t, y2: H - m.b, 'class': 'grid-l' }, g); });
    var ax = s('g', { 'class': 'ax' }, g);
    s('line', { x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }, ax);
    tks.forEach(function (t) { s('text', { x: x(t), y: H - m.b + 16, 'text-anchor': 'middle' }, ax, String(t)); });
    s('text', { x: W - m.r, y: H - m.b + 32, 'text-anchor': 'end' }, ax, 'Marginal ROAS at current spend, log scale');
    s('line', { x1: x(be), x2: x(be), y1: m.t - 6, y2: H - m.b, 'class': 'ref' }, g);
    s('text', { x: x(be) + 4, y: m.t - 8, 'class': 'lbl-ink' }, g, 'breakeven ' + ratio(be));
    legend(svg, m.l, 16, [{ kind: 'dot', label: 'Receives budget', color: 'var(--hl)' }]);
    var band = (H - m.t - m.b) / rowsS.length, items = [];
    rowsS.forEach(function (r, i) {
      var y = m.t + i * band + band / 2;
      var grows = r.delta_pct > 0.5, col = grows ? 'var(--hl)' : 'var(--ink-2)';
      s('text', { x: m.l - 8, y: y + 4, 'text-anchor': 'end', 'class': 'lbl-strong' }, g, fit(r.channel, m.l - 10));
      var note = r.held_by_rule ? 'held by rule' : r.delta_pct < -0.5 ? 'cut' : '';
      if (note) s('text', { x: m.l - 8, y: y + 19, 'text-anchor': 'end', 'class': 'lbl' }, g, note);
      s('line', { x1: x(r.marginal_roas_current_lo), x2: x(r.marginal_roas_current_hi), y1: y, y2: y, style: stroke(col, 2) }, g);
      s('circle', { cx: x(r.marginal_roas_current_median), cy: y, r: 5, style: 'fill:' + col + ';stroke:var(--surface);stroke-width:2' }, g);
      s('text', { x: x(r.marginal_roas_current_hi) + 6, y: y + 4, 'class': 'lbl-ink' }, g, ratio(r.marginal_roas_current_median));
      items.push({ x: x(r.marginal_roas_current_median), y: y, html: '<b>' + esc(r.channel) + '</b>' +
        rows([['Median', ratio(r.marginal_roas_current_median)],
          ['90% interval', ratio(r.marginal_roas_current_lo) + ' to ' + ratio(r.marginal_roas_current_hi)],
          ['Breakeven', ratio(be)], ['Change', signedPct(r.delta_pct)],
          ['Rule', r.held_by_rule ? 'held by rule' : 'free to move']]) });
    });
    interact(svg, { x: m.l, y: m.t, w: W - m.l - m.r, h: H - m.t - m.b }, items,
      { axis: 'y', label: 'Marginal ROAS per channel against breakeven. Use the arrow keys to read each channel.' });
  }

  // ---------------------------------------------------------------- page 2
  var WEEKLY = D.contributions_weekly;
  var CHANNELS = uniq(WEEKLY.map(function (r) { return r.channel; }));
  var WEEKS = uniq(WEEKLY.map(function (r) { return r.week; }));
  var BYWEEK = {};
  WEEKLY.forEach(function (r) {
    var w = BYWEEK[r.week] || (BYWEEK[r.week] = { start: r.week_start, revenue: r.revenue, v: {} });
    w.v[r.channel] = r.median;
  });
  function date(str) { var p = str.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]); }

  function drawArea(el) {
    var z = size(el), W = z.w, H = z.h, narrow = W < 520;
    var on = CHANNELS.filter(function (c) { return !state.hidden[c]; });
    var m = { l: 52, r: narrow ? 12 : 96, t: 28, b: 46 };
    var svg = svgFor(el, W, H), g = s('g', {}, svg);
    if (!on.length) { s('text', { x: m.l, y: H / 2, 'class': 'lbl-ink' }, svg, 'No channel selected.'); return; }
    var t0 = date(BYWEEK[WEEKS[0]].start), t1 = date(BYWEEK[WEEKS[WEEKS.length - 1]].start);
    var x = linear(t0, t1, m.l, W - m.r);
    var tops = WEEKS.map(function (w) {
      var acc = 0, layer = {};
      on.forEach(function (c) { layer[c] = [acc, acc + (BYWEEK[w].v[c] || 0)]; acc += BYWEEK[w].v[c] || 0; });
      return { w: w, t: date(BYWEEK[w].start), layer: layer, total: acc };
    });
    var withBase = on.indexOf('Baseline') >= 0;
    var peak = Math.max.apply(null, tops.map(function (d) { return withBase ? Math.max(d.total, BYWEEK[d.w].revenue) : d.total; }));
    var ya = axisFrom0(peak, 5);
    var y = linear(0, ya.max, H - m.b, m.t);
    yAxis(g, y, ya.ticks, m.l, W - m.r, compact);
    s('text', { x: m.l - 46, y: 14, 'class': 'lbl' }, svg, 'Weekly contribution, dataset money units');
    on.forEach(function (c) {
      var k = CHANNELS.indexOf(c), up = '', down = '';
      tops.forEach(function (d, i) { up += (i ? 'L' : 'M') + x(d.t).toFixed(1) + ',' + y(d.layer[c][1]).toFixed(1); });
      for (var i = tops.length - 1; i >= 0; i--) down += 'L' + x(tops[i].t).toFixed(1) + ',' + y(tops[i].layer[c][0]).toFixed(1);
      s('path', { d: up + down + 'Z', style: fill('var(--cat-' + k + ')') }, g);
      s('path', { d: up, style: stroke(k === 0 ? 'var(--ink-2)' : 'var(--surface)', 1) }, g);
    });
    if (withBase) {
      var rev = tops.map(function (d, i) { return (i ? 'L' : 'M') + x(d.t).toFixed(1) + ',' + y(BYWEEK[d.w].revenue).toFixed(1); }).join('');
      s('path', { d: rev, style: stroke('var(--ink)', 1.5) + ';stroke-linejoin:round' }, g);
      legend(svg, W - m.r - 150, 16, [{ kind: 'line', label: 'Observed revenue', color: 'var(--ink)', width: 1.5 }]);
    }
    var years = [], yr = new Date(t0).getUTCFullYear() + 1;
    for (; Date.UTC(yr, 0, 1) <= t1; yr++) years.push(Date.UTC(yr, 0, 1));
    var ax = s('g', { 'class': 'ax' }, g);
    s('line', { x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }, ax);
    years.forEach(function (t) {
      s('line', { x1: x(t), x2: x(t), y1: H - m.b, y2: H - m.b + 5 }, ax);
      s('text', { x: x(t), y: H - m.b + 18, 'text-anchor': 'middle' }, ax, String(new Date(t).getUTCFullYear()));
    });
    s('text', { x: W - m.r, y: H - m.b + 34, 'text-anchor': 'end' }, ax, 'Week (weekly grain, Monday start)');
    if (!narrow) {
      var last = tops[tops.length - 1], used = [];
      on.slice().reverse().forEach(function (c) {
        var a = y(last.layer[c][1]), b = y(last.layer[c][0]);
        if (b - a < 12) return;
        var ly = (a + b) / 2 + 4;
        if (used.some(function (u) { return Math.abs(u - ly) < 14; })) return;
        used.push(ly);
        s('text', { x: W - m.r + 6, y: ly, 'class': 'lbl-ink' }, g, fit(c, m.r - 8));
      });
    }
    var items = tops.map(function (d) {
      var list = on.slice().reverse().map(function (c) { return [c, money(BYWEEK[d.w].v[c])]; });
      list.push(['Revenue', money(BYWEEK[d.w].revenue)]);
      return { x: x(d.t), y: y(d.total), html: '<b>Week of ' + esc(BYWEEK[d.w].start) + '</b>' + rows(list) };
    });
    interact(svg, { x: m.l, y: m.t, w: W - m.l - m.r, h: H - m.t - m.b }, items,
      { axis: 'x', cross: true, label: 'Weekly decomposition. Use the arrow keys to step through the weeks.' });
  }

  function drawGlyphs() {
    var gl = document.querySelectorAll('#panel-contributions .glyph');
    gl.forEach(function (el) {
      var W = el.clientWidth;
      if (!W) return;
      var x = logScale(0.1, 50, 6, W - 6), svg = svgFor(el, W, 20);
      svg.setAttribute('aria-hidden', 'true');
      if (el.dataset.axis) {
        [0.1, 1, 10, 50].forEach(function (t, i) {
          s('line', { x1: x(t), x2: x(t), y1: 0, y2: 5, style: stroke('var(--mid)', 1) }, svg);
          s('text', { x: x(t), y: 17, 'text-anchor': i === 0 ? 'start' : i === 3 ? 'end' : 'middle', 'class': 'lbl' }, svg, String(t));
        });
        return;
      }
      s('line', { x1: x(1), x2: x(1), y1: 2, y2: 18, style: stroke('var(--mid)', 1) }, svg);
      s('line', { x1: x(+el.dataset.lo), x2: x(+el.dataset.hi), y1: 10, y2: 10, style: stroke('var(--ink-2)', 2) }, svg);
      s('circle', { cx: x(+el.dataset.mid), cy: 10, r: 4, style: 'fill:var(--ink);stroke:var(--surface);stroke-width:2' }, svg);
    });
  }

  // ---------------------------------------------------------------- curves (pages 3 and 4)
  function drawCurve(el, data, truth) {
    var z = size(el), W = z.w, H = z.h;
    var m = { l: 48, r: 14, t: 24, b: 44 };
    var svg = svgFor(el, W, H), g = s('g', {}, svg);
    var xmax = data[data.length - 1].spend, ymax = 0;
    data.forEach(function (r) { ymax = Math.max(ymax, r.hi, truth ? r['true'] : 0); });
    var ya = axisFrom0(ymax, 3);
    var x = linear(0, xmax, m.l, W - m.r), y = linear(0, ya.max, H - m.b, m.t);
    var obs = data[0].observed_max_spend;
    if (obs < xmax) {
      s('rect', { x: x(obs), y: m.t, width: x(xmax) - x(obs), height: H - m.t - m.b, style: fill('var(--surface-2)') }, g);
      if (x(xmax) - x(obs) > 70 && x(obs) > 150) s('text', { x: x(xmax), y: m.t - 10, 'text-anchor': 'end', 'class': 'lbl' }, g, 'extrapolated');
    }
    yAxis(g, y, ya.ticks, m.l, W - m.r, compact);
    xAxis(g, x, ticks(0, xmax, W < 360 ? 2 : 3), H - m.b, compact, 'Weekly spend', W - m.r);
    s('text', { x: 4, y: 12, 'class': 'lbl' }, svg, 'Weekly contribution');
    var band = '', i;
    data.forEach(function (r, j) { band += (j ? 'L' : 'M') + x(r.spend).toFixed(1) + ',' + y(r.hi).toFixed(1); });
    for (i = data.length - 1; i >= 0; i--) band += 'L' + x(data[i].spend).toFixed(1) + ',' + y(data[i].lo).toFixed(1);
    s('path', { d: band + 'Z', style: fill('var(--band)') }, g);
    function line(key) {
      return data.map(function (r, j) { return (j ? 'L' : 'M') + x(r.spend).toFixed(1) + ',' + y(r[key]).toFixed(1); }).join('');
    }
    s('path', { d: line('median'), style: stroke('var(--ink)', 2) + ';stroke-linejoin:round' }, g);
    if (truth) {
      s('path', { d: line('true'), style: stroke('var(--hl)', 2) + ';stroke-linejoin:round' }, g);
    } else {
      var cur = data[0].current_spend, cx = x(cur);
      s('line', { x1: cx, x2: cx, y1: m.t - 4, y2: H - m.b, style: stroke('var(--hl)', 2) }, g);
      var label = 'current ' + compact(cur), right = cx + 6 + label.length * CHAR < W - m.r;
      s('text', { x: right ? cx + 6 : cx - 6, y: m.t + 8, 'text-anchor': right ? 'start' : 'end', 'class': 'lbl-ink' }, g, label);
    }
    var items = data.map(function (r) {
      var list = [['Weekly spend', money(r.spend)], ['Median', money(r.median)], ['90% band', money(r.lo) + ' to ' + money(r.hi)]];
      if (truth) list.splice(1, 0, ['True', money(r['true'])]);
      return { x: x(r.spend), y: y(truth ? r['true'] : r.median), html: '<b>' + esc(r.channel) + '</b>' + rows(list) };
    });
    interact(svg, { x: m.l, y: m.t, w: W - m.l - m.r, h: H - m.t - m.b }, items,
      { axis: 'x', cross: true, label: data[0].channel + ' response curve. Use the arrow keys to step along the curve.' });
  }

  // ---------------------------------------------------------------- page 4
  function drawParams(el) {
    var P = D.proof_parameter_recovery;
    var z = size(el), W = z.w, H = z.h;
    var lw = Math.min(200, Math.max(120, W * 0.36));
    var m = { l: lw, r: 64, t: 30, b: 46 };
    var list = [], fam = null;
    P.forEach(function (r) {
      if (r.family !== fam) { list.push({ head: r.family }); fam = r.family; }
      var a = r.lo / r['true'], b = r.hi / r['true'];
      list.push({ r: r, mid: r.median / r['true'], lo: Math.min(a, b), hi: Math.max(a, b) });
    });
    var vals = [];
    list.forEach(function (d) { if (d.r) vals.push(d.lo, d.hi); });
    var lo = Math.min(0.25, Math.min.apply(null, vals) * 0.9), hi = Math.max(4, Math.max.apply(null, vals) * 1.1);
    var x = logScale(lo, hi, m.l, W - m.r);
    var svg = svgFor(el, W, H), g = s('g', {}, svg);
    var tks = (W < 480 ? [0.5, 1, 2, 4] : [0.25, 0.5, 1, 2, 4, 8]).filter(function (t) { return t >= lo && t <= hi; });
    tks.forEach(function (t) { s('line', { x1: x(t), x2: x(t), y1: m.t, y2: H - m.b, 'class': 'grid-l' }, g); });
    var ax = s('g', { 'class': 'ax' }, g);
    s('line', { x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }, ax);
    tks.forEach(function (t) { s('text', { x: x(t), y: H - m.b + 16, 'text-anchor': 'middle' }, ax, t + '×'); });
    s('text', { x: W - m.r, y: H - m.b + 32, 'text-anchor': 'end' }, ax, 'Posterior relative to the true value, log scale');
    s('line', { x1: x(1), x2: x(1), y1: m.t - 6, y2: H - m.b, style: stroke('var(--hl)', 2) }, g);
    s('text', { x: x(1) + 4, y: m.t - 10, 'class': 'lbl-ink' }, g, 'true value');
    var step = (H - m.t - m.b) / list.length, items = [];
    list.forEach(function (d, i) {
      var yy = m.t + i * step + step / 2;
      if (d.head) { s('text', { x: 0, y: yy + 4, 'class': 'lbl-strong' }, g, fit(d.head, m.l - 8)); return; }
      var miss = !d.r.covered, col = miss ? 'var(--neg)' : 'var(--ink)';
      s('text', { x: m.l - 8, y: yy + 4, 'text-anchor': 'end', 'class': 'lbl-ink' }, g, fit(d.r.parameter, m.l - 18));
      s('line', { x1: x(d.lo), x2: x(d.hi), y1: yy, y2: yy, style: stroke(miss ? 'var(--neg)' : 'var(--ink-2)', 2) }, g);
      s('circle', { cx: x(d.mid), cy: yy, r: 4, style: 'fill:' + col + ';stroke:var(--surface);stroke-width:2' }, g);
      if (miss) s('text', { x: W - m.r + 6, y: yy + 4, 'class': 'lbl-ink' }, g, '✕ outside');
      var f = function (v) { return Math.abs(v) >= 100 ? money(v) : String(+v.toPrecision(3)); };
      items.push({ x: x(d.mid), y: yy, html: '<b>' + esc(d.r.parameter) + '</b>' + rows([
        ['Unit', d.r.unit], ['True', f(d.r['true'])], ['Median', f(d.r.median)],
        ['90% interval', f(d.r.lo) + ' to ' + f(d.r.hi)], ['Covered', d.r.covered ? 'yes' : 'no']]) });
    });
    interact(svg, { x: m.l, y: m.t, w: W - m.l - m.r, h: H - m.t - m.b }, items,
      { axis: 'y', label: 'Parameter recovery. Use the arrow keys to read each parameter.' });
  }

  function drawGap(el) {
    var G = D.proof_attribution_gap;
    var z = size(el), W = z.w, H = z.h, narrow = W < 480;
    var m = { l: narrow ? 84 : 96, r: 56, t: 34, b: 46 };
    var vmax = 0;
    G.forEach(function (r) { vmax = Math.max(vmax, r.platform_share, r.true_share); });
    var x = linear(0, niceMax(vmax * 1.05, 4), m.l, W - m.r);
    var svg = svgFor(el, W, H), g = s('g', {}, svg);
    var tks = ticks(0, x.domain[1], narrow ? 3 : 5);
    tks.forEach(function (t) { s('line', { x1: x(t), x2: x(t), y1: m.t, y2: H - m.b, 'class': 'grid-l' }, g); });
    xAxis(g, x, tks, H - m.b, function (t) { return pct(t, 0); }, 'Share (each with its own denominator)', W - m.r);
    legend(svg, m.l, 16, [{ kind: 'hollow', label: 'Platform report', color: 'var(--ink)' },
      { kind: 'dot', label: 'True share', color: 'var(--hl)' }]);
    var band = (H - m.t - m.b) / G.length, items = [];
    G.forEach(function (r, i) {
      var yy = m.t + i * band + band / 2, noReport = r.platform_over_true_pct === null;
      s('text', { x: m.l - 14, y: yy + 4, 'text-anchor': 'end', 'class': 'lbl-strong' }, g, fit(r.channel, m.l - 16));
      s('line', { x1: x(r.platform_share), x2: x(r.true_share), y1: yy, y2: yy, style: stroke('var(--ink-2)', 1) }, g);
      s('circle', { cx: x(r.platform_share), cy: yy, r: 5, style: 'fill:var(--surface);stroke:var(--ink);stroke-width:2' }, g);
      s('circle', { cx: x(r.true_share), cy: yy, r: 5, style: 'fill:var(--hl);stroke:var(--surface);stroke-width:2' }, g);
      var gap = (r.gap_pp >= 0 ? '+' : '') + r.gap_pp.toFixed(1) + ' pp';
      s('text', { x: Math.max(x(r.platform_share), x(r.true_share)) + 9, y: yy + 4, 'class': 'lbl-ink' }, g, gap);
      if (noReport) s('text', { x: m.l + 10, y: yy + 19, 'class': 'lbl' }, g, 'no platform report');
      items.push({ x: x(r.true_share), y: yy, html: '<b>' + esc(r.channel) + '</b>' + rows([
        ['Platform share', pct(r.platform_share)], ['True share', pct(r.true_share)], ['Gap', gap],
        ['Platform over true', noReport ? 'no platform report' : signedPct(r.platform_over_true_pct)]]) });
    });
    interact(svg, { x: m.l, y: m.t, w: W - m.l - m.r, h: H - m.t - m.b }, items,
      { axis: 'y', label: 'Attribution gap per channel. Use the arrow keys to read each channel.' });
  }

  // ---------------------------------------------------------------- registry and resize
  var draws = [];
  function register(id, fn) {
    var el = document.getElementById(id);
    if (el) draws.push({ el: el, fn: fn, w: 0 });
  }
  register('c-spend', drawSpend);
  register('c-mroas', drawMroas);
  register('c-area', drawArea);
  register('c-params', drawParams);
  register('c-gap', drawGap);
  document.querySelectorAll('[data-curve]').forEach(function (el) {
    var rowsC = D.response_curves.filter(function (r) { return r.channel === el.dataset.curve; });
    draws.push({ el: el, fn: function (e) { drawCurve(e, rowsC, false); }, w: 0 });
  });
  document.querySelectorAll('[data-pcurve]').forEach(function (el) {
    var rowsC = D.proof_response_curves.filter(function (r) { return r.channel === el.dataset.pcurve; });
    draws.push({ el: el, fn: function (e) { drawCurve(e, rowsC, true); }, w: 0 });
  });

  function drawVisible(force) {
    draws.forEach(function (d) {
      var w = d.el.clientWidth;
      if (!w || d.el.offsetParent === null) return;
      if (force || w !== d.w) { d.w = w; d.fn(d.el); }
    });
    drawGlyphs();
  }
  var pending = 0;
  function schedule(force) {
    cancelAnimationFrame(pending);
    pending = requestAnimationFrame(function () { drawVisible(force); });
  }
  if (window.ResizeObserver) {
    var ro = new ResizeObserver(function () { schedule(false); });
    draws.forEach(function (d) { ro.observe(d.el); });
  } else {
    window.addEventListener('resize', function () { schedule(false); });
  }

  // ---------------------------------------------------------------- tabs
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));
  function select(slug, focus) {
    var found = tabs.some(function (t) { return t.dataset.slug === slug; });
    if (!found) slug = tabs[0].dataset.slug;
    tabs.forEach(function (t) {
      var on = t.dataset.slug === slug;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
      if (on && focus) t.focus();
    });
    if (location.hash !== '#' + slug && history.replaceState) history.replaceState(null, '', '#' + slug);
    hideTip();
    schedule(false);
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { select(t.dataset.slug, false); });
    t.addEventListener('keydown', function (e) {
      var j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (j === undefined) return;
      e.preventDefault();
      select(tabs[(j + tabs.length) % tabs.length].dataset.slug, true);
    });
  });
  window.addEventListener('hashchange', function () { select(location.hash.slice(1), false); });

  // ---------------------------------------------------------------- scenario and channel controls
  var segs = Array.prototype.slice.call(document.querySelectorAll('.seg'));
  function setScenario(sc, focus) {
    state.scenario = sc;
    segs.forEach(function (b) {
      var on = b.dataset.scenario === sc;
      b.setAttribute('aria-checked', on ? 'true' : 'false');
      b.tabIndex = on ? 0 : -1;
      if (on && focus) b.focus();
    });
    document.querySelectorAll('[data-scenario-block]').forEach(function (n) {
      n.hidden = n.getAttribute('data-scenario-block') !== sc;
    });
    draws.forEach(function (d) { if (d.el.id === 'c-spend' || d.el.id === 'c-mroas') d.w = 0; });
    schedule(false);
  }
  segs.forEach(function (b, i) {
    b.addEventListener('click', function () { setScenario(b.dataset.scenario, false); });
    b.addEventListener('keydown', function (e) {
      var j = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1 }[e.key];
      if (j === undefined) return;
      e.preventDefault();
      setScenario(segs[(j + segs.length) % segs.length].dataset.scenario, true);
    });
  });
  document.querySelectorAll('.chip').forEach(function (b) {
    b.addEventListener('click', function () {
      var on = b.getAttribute('aria-pressed') !== 'true';
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      state.hidden[b.dataset.channel] = !on;
      draws.forEach(function (d) { if (d.el.id === 'c-area') d.w = 0; });
      schedule(false);
    });
  });

  select(location.hash.slice(1), false);
})();
