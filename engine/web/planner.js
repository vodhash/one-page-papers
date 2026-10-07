/* one-page-papers: the wall planner of a series page. It draws the posters of the series to scale
   on a wall, in the print format, layout, frames and theme chosen, with their sizes and the height
   to hang them at, and shows the download of each poster in that format and theme. Everything
   happens here: nothing is stored or sent. Without it, the page lists the posters and their PDFs. */
(function () {
  'use strict';
  var box = document.querySelector('[data-planner]');
  var list = document.querySelector('.series-dl');
  if (!box || !list || !document.createElementNS) return;
  var NS = 'http://www.w3.org/2000/svg';
  var HANG = +box.getAttribute('data-hang') || 145;  // cm from the floor to the centre of the composition
  var PERSON = 170, PERSON_W = 50, PERSON_GAP = 40;  // cm: the figure beside the wall, for scale
  var A_ORDER = ['A3', 'A2', 'A1', 'A0'];
  var form = box.querySelector('.pl-form');
  var canvas = box.querySelector('.pl-canvas');
  var sum = box.querySelector('.pl-sum');
  var now = list.querySelector('.sdl-now');
  var rows = Array.prototype.slice.call(list.querySelectorAll('.sdl > li'));
  var n = rows.length;

  function picked(name) {
    var el = form.querySelector('input[name=' + name + ']:checked') || form.querySelector('input[name=' + name + ']');
    return el;
  }
  function num(name, max) {
    var v = parseFloat(String(form.elements[name].value).replace(',', '.'));
    return isFinite(v) ? Math.min(Math.max(v, 0), max) : 0;
  }
  function round1(x) { return Math.round(x * 10) / 10; }
  function trim(x) { return String(round1(x)).replace(/\.0$/, ''); }

  // the state of the form: sizes in cm
  function state() {
    var f = picked('pl-format');
    var theme = picked('pl-theme');
    return {
      key: f.value, label: f.getAttribute('data-label'),
      file: f.getAttribute('data-file'), us: f.hasAttribute('data-us'),
      w: +f.getAttribute('data-w') / 10, h: +f.getAttribute('data-h') / 10,
      layout: picked('pl-layout').value,
      gap: num('pl-gap', 60), frame: num('pl-frame', 15), mat: num('pl-mat', 30),
      theme: theme ? theme.value : ''
    };
  }

  // a length: cm, and inches after it with a US format
  function len(cm, s) { return trim(cm) + ' cm' + (s.us ? ' (' + trim(cm / 2.54) + ' in)' : ''); }
  function size(w, h, s) {
    return trim(w) + ' × ' + trim(h) + ' cm' +
      (s.us ? ' (' + trim(w / 2.54) + ' × ' + trim(h / 2.54) + ' in)' : '');
  }

  // where each frame goes, from the top left corner of the composition, in cm
  function place(s, fw, fh) {
    var spec = [], k, c;
    if (s.layout === 'row') spec = [n];
    else if (s.layout === '3over2') spec = [3, 2];
    else {
      c = s.layout === 'cols3' ? 3 : 2;
      for (k = n; k > 0; k -= c) spec.push(Math.min(c, k));
    }
    var cols = Math.max.apply(null, spec);
    var W = cols * fw + (cols - 1) * s.gap, H = spec.length * fh + (spec.length - 1) * s.gap;
    var cells = [];
    spec.forEach(function (k, r) {
      var x0 = s.layout === '3over2' ? (W - (k * fw + (k - 1) * s.gap)) / 2 : 0;
      for (var j = 0; j < k; j++) cells.push({ x: x0 + j * (fw + s.gap), y: r * (fh + s.gap) });
    });
    return { cells: cells, w: W, h: H, rows: spec.length };
  }

  function el(parent, name, attrs, text) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  // a dimension line with its ticks, and its label (rotated for a vertical one)
  function dim(g, x1, y1, x2, y2, label, cls, textCls) {
    var v = x1 === x2;
    el(g, 'path', { 'class': 'dim ' + (cls || ''), d: 'M' + x1 + ' ' + y1 + 'L' + x2 + ' ' + y2 +
      (v ? 'M' + (x1 - 5) + ' ' + y1 + 'h10M' + (x2 - 5) + ' ' + y2 + 'h10'
         : 'M' + x1 + ' ' + (y1 - 5) + 'v10M' + x2 + ' ' + (y2 - 5) + 'v10') });
    if (v) {
      var cy = (y1 + y2) / 2;
      el(g, 'text', { x: x1 - 8, y: cy, 'text-anchor': 'middle', transform: 'rotate(-90 ' + (x1 - 8) + ' ' + cy + ')',
        'class': textCls || '' }, label);
    } else {
      el(g, 'text', { x: (x1 + x2) / 2, y: y1 - 8, 'text-anchor': 'middle', 'class': textCls || '' }, label);
    }
  }
  // a standing figure, 50 by 172 units, its feet at (0, 0) of its box
  var FIGURE = 'M25 1a10.5 10.5 0 1 1 0 21a10.5 10.5 0 1 1 0-21zM14 25q11-4 22 0l6 3q3 2 3 6l1 50q0 4-3 4h-1q-3 0-3-4' +
    'l-1-36-2 0 1 50-1 70q0 4-4 4h-2q-3 0-3-4l-1-66h-2l-1 66q0 4-3 4h-2q-4 0-4-4l-1-70 1-50h-2l-1 36q0 4-3 4h-1q-3 0-3-4' +
    'l1-50q0-4 3-6z';

  function textWidth(t) { return t.length * 6.6; }  // at 14px, enough to decide whether a label fits

  function draw(s) {
    var fw = s.w + 2 * (s.mat + s.frame), fh = s.h + 2 * (s.mat + s.frame);
    var c = place(s, fw, fh);
    var top = HANG + c.h / 2, bottom = HANG - c.h / 2;
    var cw = Math.max(canvas.clientWidth, 280);
    var padL = 16, padR = 52, padT = 64, padB = 34, hangGap = 34;
    var spanW = PERSON_W + PERSON_GAP + c.w;
    var skyCm = Math.max(top, PERSON) + 16, floorCm = Math.min(bottom, 0);
    var scale = (cw - padL - padR - hangGap) / spanW;
    var maxH = Math.max(300, Math.min(640, window.innerHeight * 0.72));
    if ((skyCm - floorCm) * scale + padT + padB > maxH) scale = (maxH - padT - padB) / (skyCm - floorCm);
    var H = Math.round((skyCm - floorCm) * scale + padT + padB);
    var used = spanW * scale + hangGap;
    var x0 = padL + (cw - padL - padR - used) / 2;          // left of the figure
    var ox = x0 + (PERSON_W + PERSON_GAP) * scale + hangGap; // left of the composition
    var floorY = padT + (skyCm - Math.max(floorCm, 0)) * scale;
    var X = function (cm) { return ox + cm * scale; };
    var Y = function (cmUp) { return floorY - cmUp * scale; };  // height above the floor
    var r1 = function (x) { return Math.round(x * 10) / 10; };

    var svg = el(null, 'svg', { 'class': 'pl-svg', viewBox: '0 0 ' + cw + ' ' + H, width: cw, height: H, role: 'img',
      'aria-label': 'The wall, drawn to scale: ' + n + ' posters at ' + s.label + ', ' + size(c.w, c.h, s) +
        ' in all, centred ' + HANG + ' cm above the floor, beside a figure 170 cm tall.' });
    // the floor
    el(svg, 'rect', { 'class': 'floor', x: 0, y: floorY, width: cw, height: H - floorY });
    el(svg, 'path', { 'class': 'floor-line', d: 'M0 ' + floorY + 'H' + cw });
    // the figure
    var k = scale * PERSON / 172;
    el(svg, 'path', { 'class': 'person', d: FIGURE,
      transform: 'translate(' + r1(x0 + (PERSON_W * scale - 50 * k) / 2) + ' ' + r1(floorY - 172 * k) + ') scale(' + k + ')' });
    // the frames
    var g = el(svg, 'g', { 'class': 'framed' });
    var topY = Y(top);
    c.cells.forEach(function (cell, i) {
      var x = X(cell.x), y = topY + cell.y * scale, row = rows[i];
      if (s.frame > 0) el(g, 'rect', { 'class': 'moulding', x: r1(x), y: r1(y), width: r1(fw * scale), height: r1(fh * scale) });
      var inset = s.frame * scale;
      if (s.mat > 0) el(g, 'rect', { 'class': 'matboard', x: r1(x + inset), y: r1(y + inset),
        width: r1((fw - 2 * s.frame) * scale), height: r1((fh - 2 * s.frame) * scale) });
      inset = (s.frame + s.mat) * scale;
      var theme = s.theme || row.getAttribute('data-light');
      el(g, 'image', { href: row.getAttribute('data-src-' + theme), x: r1(x + inset), y: r1(y + inset),
        width: r1(s.w * scale), height: r1(s.h * scale), preserveAspectRatio: 'none' });
      el(g, 'rect', { 'class': 'edge', x: r1(x + inset), y: r1(y + inset), width: r1(s.w * scale), height: r1(s.h * scale) });
    });
    // the dimensions: the whole width above, a frame (and a gap) above the first row, the height on the right
    var total = len(c.w, s);
    dim(svg, r1(X(0)), r1(topY - 40), r1(X(c.w)), r1(topY - 40), total);
    var frameLabel = len(fw, s);
    if (textWidth(frameLabel) + 8 < fw * scale && n > 1) {
      dim(svg, r1(X(c.cells[0].x)), r1(topY - 12), r1(X(c.cells[0].x + fw)), r1(topY - 12), frameLabel);
      var gx = c.cells[0].x + fw, gapLabel = len(s.gap, s);
      if (s.gap > 0 && c.cells[1] && c.cells[1].y === 0 && textWidth(gapLabel) + textWidth(frameLabel) / 2 + 16 < (fw / 2 + s.gap) * scale) {
        dim(svg, r1(X(gx)), r1(topY - 12), r1(X(gx + s.gap)), r1(topY - 12), '');
        el(svg, 'text', { x: r1(X(gx + s.gap / 2)), y: r1(topY - 20), 'text-anchor': 'middle' }, gapLabel);
      }
    }
    dim(svg, r1(X(c.w) + 30), r1(topY), r1(X(c.w) + 30), r1(Y(bottom)), len(c.h, s));
    // the hanging height: from the floor to the centre, and the centre line
    var hx = r1(ox - hangGap / 2 - 2);
    el(svg, 'path', { 'class': 'centre', d: 'M' + hx + ' ' + r1(Y(HANG)) + 'H' + r1(X(0) - 4) });
    dim(svg, hx, r1(Y(HANG)), hx, r1(floorY), HANG + ' cm' + (s.us ? ' (' + trim(HANG / 2.54) + ' in)' : ''),
      'dim-hang', 'hang');
    canvas.replaceChildren ? canvas.replaceChildren(svg) : (canvas.innerHTML = '', canvas.appendChild(svg));
    return { c: c, fw: fw, fh: fh, top: top, bottom: bottom };
  }

  function summary(s, d) {
    var items = [
      ['Composition', size(d.c.w, d.c.h, s)],
      ['Each frame', size(d.fw, d.fh, s) + ' <span>· poster ' + size(s.w, s.h, s) +
        (s.mat > 0 ? ', mat ' + len(s.mat, s) : '') + (s.frame > 0 ? ', frame ' + len(s.frame, s) : ', no frame') + '</span>'],
      ['Gaps', len(s.gap, s) + ' between frames'],
      ['Hang', 'centre ' + len(HANG, s) + ' from the floor <span>· top edge at ' + len(d.top, s) +
        ', bottom edge at ' + len(d.bottom, s) + '</span>']
    ];
    var html = items.map(function (it) { return '<dt>' + it[0] + '</dt><dd>' + it[1] + '</dd>'; }).join('');
    if (d.bottom < 0) {
      html += '<dd class="warn">Too tall to centre at ' + HANG + ' cm: the composition would go below the floor. ' +
        'Choose a smaller format, or a layout with fewer rows.</dd>';
    } else if (d.bottom < 30) {
      html += '<dd class="warn">The bottom edge comes within 30 cm of the floor: a smaller format, or fewer rows, ' +
        'would leave more room.</dd>';
    } else if (d.top > 250) {
      html += '<dd class="warn">The top edge is above 250 cm, higher than many ceilings.</dd>';
    }
    sum.innerHTML = html;
  }

  // the downloads: the PDF of each poster in the format and theme chosen, and with a US format the
  // zips of the US formats too
  function downloads(s) {
    var themeName = s.theme || 'first';
    list.classList.toggle('us', s.us);
    rows.forEach(function (row) {
      var theme = s.theme || row.getAttribute('data-light');
      Array.prototype.forEach.call(row.querySelectorAll('a[data-t]'), function (a) {
        a.classList.toggle('on', a.getAttribute('data-f') === s.file && a.getAttribute('data-t') === theme);
      });
      var warn = row.querySelector('.sdl-warn');
      var min = row.getAttribute('data-min');
      var low = A_ORDER.indexOf(s.key) >= 0 && A_ORDER.indexOf(s.key) < A_ORDER.indexOf(min);
      warn.hidden = !low;
      warn.textContent = low ? 'At ' + s.key + ', its body text prints under 8 pt: print it from ' + min + '.' : '';
    });
    var fmt = A_ORDER.indexOf(s.key) >= 0 ? s.key + ', from the A PDF, which prints at A3 to A0' : s.label;
    now.textContent = fmt + ', in the ' + themeName + ' theme' + (s.theme ? '' : ' of each poster') + '.';
  }

  var last = null;
  function update() {
    var s = state();
    summary(s, draw(s));
    downloads(s);
    last = s;
  }

  // start in the theme of the mode of the site, when every poster has it
  var dark = document.documentElement.getAttribute('data-theme') === 'dark';
  var start = form.querySelector('input[name=pl-theme][value=' + (dark ? 'genesis' : 'ivory') + ']');
  if (start) start.checked = true;
  box.querySelector('.pl-body').hidden = false;
  form.addEventListener('input', update);
  form.addEventListener('change', update);
  form.addEventListener('submit', function (e) { e.preventDefault(); });
  var width = canvas.clientWidth;
  var onResize = function () {
    if (canvas.clientWidth !== width) {
      width = canvas.clientWidth;
      if (last) summary(last, draw(last));
    }
  };
  if (window.ResizeObserver) new ResizeObserver(onResize).observe(canvas);
  else window.addEventListener('resize', onResize);
  update();
})();
