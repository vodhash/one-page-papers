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
    var printIt = poster.querySelector('[data-print-it]');
    var printBase = printIt ? printIt.getAttribute('href') : '';
    var render = function () {
      var t = current();
      // the print guide opens on the theme shown
      if (printIt) printIt.setAttribute('href', printBase + '&theme=' + encodeURIComponent(t));
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

  // The print guide, opened from the Print it button of a poster (?poster=<slug>&theme=<theme>):
  // a box with the Print from of that poster, a theme to choose and the links to its PDFs.
  var box = document.getElementById('for-poster');
  var dataEl = document.getElementById('print-data');
  if (box && dataEl) {
    var params = new URLSearchParams(location.search);
    var printData = null;
    try { printData = JSON.parse(dataEl.textContent); } catch (e) { /* the guide shows on its own */ }
    var slug = params.get('poster');
    var info = printData && Object.prototype.hasOwnProperty.call(printData.posters, slug) ? printData.posters[slug] : null;
    if (info) {
      var name = info[0], category = info[1], min = info[2], themes = info[3];
      var theme = themes.indexOf(params.get('theme')) >= 0 ? params.get('theme') : themes[0];
      var make = function (tag, cls, content) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (content) e.textContent = content;
        return e;
      };
      var posterLink = box.querySelector('.fp-link');
      posterLink.href = '../' + slug + '/';
      posterLink.textContent = name;
      // Print from: the body is 8 to 11 pt at that size, and grows by about 1.4 at each size up
      var sizes = printData.sizes.slice(printData.sizes.indexOf(min));
      var floors = [11, 16, 22];
      var printFrom = 'Print from ' + min + ': its body text is 8 to 11 pt at ' + min;
      var up = sizes.slice(1).map(function (s, i) { return 'at least ' + floors[i] + ' pt at ' + s; });
      if (up.length) printFrom += ', ' + up.join(', ');
      box.querySelector('.fp-print').textContent = printFrom + '.';
      var boxImg = document.createElement('img');
      boxImg.width = 600;
      boxImg.height = 849;
      boxImg.decoding = 'async';
      box.querySelector('.fp-mat').appendChild(boxImg);
      var pills = box.querySelector('.fp-themes');
      var files = box.querySelector('.fp-files');
      var advice = box.querySelector('.fp-advice');
      var showBox = function () {
        boxImg.src = '../previews/' + slug + '-' + theme + '-600.webp';
        boxImg.alt = 'Preview of the poster in the ' + theme + ' theme';
        each('button', function (b) { b.setAttribute('aria-pressed', String(b.value === theme)); }, pills);
        advice.textContent = printData.themes[theme][2]
          ? 'A dark theme: best printed by a lab that prints deep blacks. On white aluminium, prefer a light theme.'
          : 'A light theme: it suits paper, and it is the one to choose on white aluminium.';
        files.textContent = '';
        printData.formats.forEach(function (f) {
          var li = make('li');
          var a = make('a', 'btn btn-line', f[1] + ' · ' + theme);
          a.href = printData.pdf.replace('{category}', category).replace('{file}', slug + '-' + f[0] + '-' + theme + '.pdf');
          a.type = 'application/pdf';
          li.appendChild(a);
          li.appendChild(make('span', 'fp-what', f[0] === 'A' ? 'Any ISO A size; body at 8 pt or more at ' + sizes.join(', ') : 'Its own layout'));
          files.appendChild(li);
        });
        var li = make('li');
        var a = make('a', 'btn btn-line', 'US formats');
        a.href = printData.us.replace('{category}', category);
        li.appendChild(a);
        li.appendChild(make('span', 'fp-what', 'Every poster of its category, in the zip ' + category + '-us.zip'));
        files.appendChild(li);
      };
      themes.forEach(function (t) {
        var b = make('button', 'pill');
        b.type = 'button';
        b.value = t;
        var sw = make('span', 'swatch');
        sw.setAttribute('aria-hidden', 'true');
        sw.style.setProperty('--sw', printData.themes[t][0]);
        sw.style.setProperty('--sa', printData.themes[t][1]);
        b.appendChild(sw);
        b.appendChild(document.createTextNode(t));
        b.addEventListener('click', function () {
          theme = t;
          showBox();
          try { history.replaceState(null, '', '?poster=' + slug + '&theme=' + t); } catch (e) { /* file: */ }
        });
        pills.appendChild(b);
      });
      showBox();
      box.hidden = false;
    }
  }

  // An annotated reading page: the notes in the margin of a wide screen, pushed down so that none
  // covers the one above it, and a button to hide them, remembered. Without this script, or on a
  // small screen, the number after each marked phrase opens its note in the text.
  var annotated = document.querySelector('.annotated');
  if (annotated) {
    var NOTES = 'one-page-papers:notes';
    var textEl = annotated.querySelector('.text');
    var notes = Array.prototype.slice.call(annotated.querySelectorAll('.sidenote'));
    var wide = window.matchMedia('(min-width: 1180px)');
    var toggle = annotated.querySelector('[data-notes-toggle]');
    var off = false;
    try { off = localStorage.getItem(NOTES) === 'off'; } catch (e) { /* no storage: the notes show */ }
    var place = function () {
      notes.forEach(function (n) { n.style.top = ''; });
      textEl.style.minHeight = '';
      if (!wide.matches || off) return;
      // each note starts level with the line where its phrase begins
      var origin = textEl.getBoundingClientRect().top;
      var tops = notes.map(function (n) {
        var mark = annotated.querySelector('#an-' + n.getAttribute('data-note'));
        return mark ? mark.getBoundingClientRect().top - origin : n.offsetTop;
      });
      var last = -Infinity;
      notes.forEach(function (n, i) {
        var top = Math.max(tops[i], last + 18);
        n.style.top = top + 'px';
        last = top + n.offsetHeight;
      });
      if (last > textEl.offsetHeight) textEl.style.minHeight = last + 'px';
    };
    var setOff = function (v) {
      off = v;
      annotated.classList.toggle('notes-off', off);
      if (toggle) toggle.setAttribute('aria-pressed', String(!off));
      place();
    };
    if (toggle) {
      toggle.parentNode.hidden = false;
      toggle.addEventListener('click', function () {
        setOff(!off);
        try { localStorage.setItem(NOTES, off ? 'off' : 'on'); } catch (e) { /* lasts for this page */ }
      });
    }
    // a note and its phrase light up together
    each('mark.anno[data-note], .sidenote', function (e) {
      var pair = function (on) {
        each('[data-note="' + e.getAttribute('data-note') + '"]', function (x) {
          if (x.matches('mark, .sidenote')) x.classList.toggle('hot', on);
        }, annotated);
      };
      e.addEventListener('mouseenter', function () { pair(true); });
      e.addEventListener('mouseleave', function () { pair(false); });
    }, annotated);
    setOff(off);
    wide.addEventListener('change', place);
    window.addEventListener('load', place);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(place);
    if (window.ResizeObserver) {
      var width = textEl.offsetWidth;
      new ResizeObserver(function () {
        if (textEl.offsetWidth !== width) { width = textEl.offsetWidth; place(); }
      }).observe(textEl);
    }
  }

  // A teaching kit: print it without the answers, with them, or the answers alone. Without this
  // script, printing the page prints it all, the answers on a page of their own.
  var kit = document.querySelector('[data-teach]');
  if (kit && window.print) {
    var PRINT_MODES = ['print-no-answers', 'print-answers-only'];
    var clear = function () { PRINT_MODES.forEach(function (c) { root.classList.remove(c); }); };
    window.addEventListener('afterprint', clear);
    each('[data-print]', function (b) {
      b.addEventListener('click', function () {
        clear();
        var how = b.getAttribute('data-print');
        if (how !== 'all') root.classList.add('print-' + how);
        window.print();
      });
    }, kit);
    kit.querySelector('.teach-print').hidden = false;
  }

  apply(mode());
})();
