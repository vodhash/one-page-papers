/* one-page-papers: the theme button, the menu on small screens, the filters of the collection,
   the themes of a poster and its wallpapers. Every page works without it: the colours follow the
   system, the whole collection shows, and a poster page offers the PDF of each theme. */
(function () {
  'use strict';
  var root = document.documentElement;
  // the folder of this script, where pdf.js is (assets/pdfjs/)
  var assets = document.currentScript ? document.currentScript.src : location.href;
  var KEY = 'one-page-papers:theme';
  var system = window.matchMedia('(prefers-color-scheme: dark)');
  var onMode = [];

  function saved() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function mode() {
    return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }
  function each(selector, f, scope) {
    Array.prototype.forEach.call((scope || document).querySelectorAll(selector), f);
  }

  // The theme of the site. The dark <source> of each preview follows it rather than the system.
  function apply(m) {
    root.setAttribute('data-theme', m);
    var media = m === 'dark' ? 'all' : 'not all';
    each('source[data-dark]', function (s) { if (s.media !== media) s.media = media; });
    var button = document.querySelector('.mode');
    if (button) button.setAttribute('aria-pressed', String(m === 'dark'));
    onMode.forEach(function (f) { f(m); });
  }
  var modeButton = document.querySelector('.mode');
  if (modeButton) {
    modeButton.addEventListener('click', function () {
      var m = mode() === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(KEY, m); } catch (e) { /* private mode: the choice lasts for this page */ }
      apply(m);
    });
  }
  system.addEventListener('change', function (e) {
    var s = saved();
    if (s !== 'dark' && s !== 'light') apply(e.matches ? 'dark' : 'light');
  });

  // The menu of small screens
  var burger = document.querySelector('.burger');
  var nav = document.getElementById('nav');
  if (burger && nav) {
    var setOpen = function (open) {
      burger.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('open', open);
    };
    burger.addEventListener('click', function () {
      setOpen(burger.getAttribute('aria-expanded') !== 'true');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('open')) {
        setOpen(false);
        burger.focus();
      }
    });
    document.addEventListener('click', function (e) {
      if (nav.classList.contains('open') && !e.target.closest('.site-header')) setOpen(false);
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });
  }

  // The filters of the collection, which ?category= in the address also sets
  var filters = document.querySelector('.filters');
  if (filters) {
    var status = document.getElementById('filter-status');
    var show = function (category, announce) {
      var n = 0;
      each('button', function (b) {
        b.setAttribute('aria-pressed', String(b.getAttribute('data-filter') === category));
      }, filters);
      each('.cards > li', function (card) {
        var hit = !category || card.getAttribute('data-category') === category;
        card.hidden = !hit;
        if (hit) n += 1;
      });
      if (announce && status) status.textContent = n + (n === 1 ? ' poster' : ' posters');
    };
    filters.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      var category = b.getAttribute('data-filter');
      show(category, true);
      history.replaceState(null, '', (category ? '?category=' + category : location.pathname) + '#collection');
    });
    var asked = new URLSearchParams(location.search).get('category');
    var known = Array.prototype.some.call(filters.querySelectorAll('button'), function (b) {
      return b.getAttribute('data-filter') === asked;
    });
    if (asked && known) show(asked, false);
  }

  // A poster page: the pills choose the theme of the preview and of the download buttons.
  // Until one is pressed, the theme shown follows the mode of the site (the CSS shows its buttons).
  var poster = document.querySelector('[data-poster]');
  if (poster) {
    var picture = poster.querySelector('.wall picture');
    var current = function () {
      return poster.getAttribute('data-picked') || poster.getAttribute(mode() === 'dark' ? 'data-dark' : 'data-light');
    };
    var render = function () {
      var t = current();
      each('[data-pick]', function (p) { p.setAttribute('aria-pressed', String(p.getAttribute('data-pick') === t)); }, poster);
      each('.dl a[data-t]', function (a) { a.classList.toggle('on', a.getAttribute('data-t') === t); }, poster);
      each('.shown', function (s) { s.textContent = t; }, poster);
      // the wallpaper starts in the theme shown
      var radio = poster.querySelector('input[name=wp-theme][value="' + t + '"]');
      if (radio && !radio.checked) {
        radio.checked = true;
        radio.dispatchEvent(new Event('change', { bubbles: true }));
      }
    };
    each('[data-pick]', function (p) {
      p.addEventListener('click', function () {
        poster.setAttribute('data-picked', p.getAttribute('data-pick'));
        each('source, img', function (e) { e.srcset = p.getAttribute('data-srcset'); }, picture);
        render();
      });
    }, poster);
    onMode.push(render);
  }

  // The wallpaper of a poster: its A PDF in the theme chosen, drawn by pdf.js (loaded on the first
  // request) on a canvas of the size of the screen, filled with the paper colour of the theme, the
  // poster centred and as large as a margin allows. Nothing is sent anywhere: the PNG is made here.
  var wall = document.querySelector('[data-wallpaper]');
  if (wall && window.HTMLCanvasElement && window.Promise && window.URL) {
    var form = wall.querySelector('.wp-form');
    var status = wall.querySelector('.wp-status');
    var result = wall.querySelector('.wp-result');
    var button = form.querySelector('button[type=submit]');
    var lib = null, docs = {}, blobUrl = null, busy = false;
    var pdfjs = function () {
      if (!lib) {
        lib = import(new URL('pdfjs/pdf.min.mjs', assets).href).then(function (m) {
          m.GlobalWorkerOptions.workerSrc = new URL('pdfjs/pdf.worker.min.mjs', assets).href;
          return m;
        });
        lib.catch(function () { lib = null; });
      }
      return lib;
    };
    var load = function (url) {
      if (!docs[url]) {
        docs[url] = Promise.all([pdfjs(), fetch(url).then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.arrayBuffer();
        })]).then(function (both) {
          return both[0].getDocument({ data: new Uint8Array(both[1]), isEvalSupported: false }).promise;
        });
        docs[url].catch(function () { delete docs[url]; });
      }
      return docs[url];
    };
    var picked = function (name) { return form.querySelector('input[name=' + name + ']:checked'); };
    var say = function (text) { status.textContent = text; };
    form.hidden = false;
    form.addEventListener('change', function () { result.hidden = true; say(''); });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (busy) return;
      var size = picked('wp-size'), theme = picked('wp-theme');
      var W = +size.getAttribute('data-w'), H = +size.getAttribute('data-h');
      var paper = theme.getAttribute('data-paper');
      busy = true;
      button.disabled = true;
      result.hidden = true;
      say('Loading the poster\u2026');
      load(theme.getAttribute('data-pdf')).then(function (doc) {
        return doc.getPage(1);
      }).then(function (page) {
        say('Drawing it\u2026');
        var one = page.getViewport({ scale: 1 });
        var margin = Math.round(Math.min(W, H) * 0.07);
        var scale = Math.min((W - 2 * margin) / one.width, (H - 2 * margin) / one.height);
        var viewport = page.getViewport({ scale: scale });
        var sheet = document.createElement('canvas');
        sheet.width = Math.floor(viewport.width);
        sheet.height = Math.floor(viewport.height);
        return page.render({ canvas: sheet, canvasContext: sheet.getContext('2d'), viewport: viewport,
          background: paper }).promise.then(function () { return sheet; });
      }).then(function (sheet) {
        var canvas = document.createElement('canvas');
        canvas.width = W;
        canvas.height = H;
        var ctx = canvas.getContext('2d');
        ctx.fillStyle = paper;
        ctx.fillRect(0, 0, W, H);
        ctx.drawImage(sheet, Math.round((W - sheet.width) / 2), Math.round((H - sheet.height) / 2));
        return new Promise(function (resolve, reject) {
          canvas.toBlob(function (b) { if (b) resolve(b); else reject(new Error('toBlob')); }, 'image/png');
        });
      }).then(function (blob) {
        if (blobUrl) URL.revokeObjectURL(blobUrl);
        blobUrl = URL.createObjectURL(blob);
        var name = wall.getAttribute('data-slug') + '-' + theme.value + '-' + W + 'x' + H + '.png';
        var img = result.querySelector('img');
        img.src = blobUrl;
        img.alt = 'The wallpaper, ' + W + ' by ' + H + ' pixels, in the ' + theme.value + ' theme';
        var a = result.querySelector('a');
        a.href = blobUrl;
        a.download = name;
        a.textContent = 'Download the PNG \u00b7 ' + (blob.size / 1e6).toFixed(1) + ' MB';
        result.hidden = false;
        say('Ready: ' + W + '\u00a0\u00d7\u00a0' + H + ' pixels.');
      }).catch(function () {
        say('The wallpaper could not be made. Check the connection, or download the PDF above.');
      }).then(function () {
        busy = false;
        button.disabled = false;
      });
    });
  }

  apply(mode());
})();
