/* one-page-papers: the theme button, the menu on small screens, the search and the filters of the
   collection, the themes of a poster and its wallpapers, the print guide, the margin notes, the
   teaching kits, the blocks that scroll and the large images. Every page works without it: the
   colours follow the system, the whole collection shows, and a poster page offers the PDF of each
   theme. Each part is a function of its own, which does nothing on a page that lacks what it needs. */
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
  // An event for Umami, the analytics of the site, when its script has loaded: a blocker or
  // make serve leaves window.umami undefined, and nothing is sent. Links and buttons that need no
  // script say their event in data-umami-event attributes, which Umami reads on a click.
  function track(name, data) {
    try { if (window.umami && window.umami.track) window.umami.track(name, data); } catch (e) { /* not counted */ }
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

  function themeButton() {
    var button = document.querySelector('.mode');
    if (button) {
      button.addEventListener('click', function () {
        var m = mode() === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem(KEY, m); } catch (e) { /* private mode: the choice lasts for this page */ }
        apply(m);
      });
    }
    system.addEventListener('change', function (e) {
      var s = saved();
      if (s !== 'dark' && s !== 'light') apply(e.matches ? 'dark' : 'light');
    });
  }

  // The menu of small screens
  function menu() {
    var burger = document.querySelector('.burger');
    var nav = document.getElementById('nav');
    if (!burger || !nav) return;
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

  // The collection of the home page: a search (?q= in the address), the filters (?category=) and
  // pages of PER_PAGE posters (?page=). The search keeps the posters whose category, title,
  // authors, year, summary or slug hold every word typed, accents and case aside, and the count of
  // each filter follows it. Without this script the whole collection shows, and the filters lead to
  // the pages of the categories.
  function collection() {
    var filters = document.querySelector('.filters');
    var list = document.querySelector('.cards');
    if (!filters || !list) return;
    var PER_PAGE = 24;
    var status = document.getElementById('filter-status');
    var heading = document.getElementById('collection-title');
    var finder = document.querySelector('.finder');
    var input = finder ? finder.querySelector('input') : null;
    var clear = finder ? finder.querySelector('.search-clear') : null;
    var noHits = document.querySelector('.no-hits');
    var cards = Array.prototype.slice.call(list.children);
    var fold = function (s) {
      return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[\u2018\u2019]/g, "'");
    };
    var words = cards.map(function (card) {
      var parts = Array.prototype.map.call(card.querySelectorAll('.eyebrow, .card-title, .by, .sum, .adds'),
        function (e) { return e.textContent; });
      var link = card.querySelector('.card-title a');
      if (link) parts.push(link.getAttribute('href').replace(/[\/-]/g, ' '));  // the slug: rfc 1149
      return fold(parts.join(' ').replace(/\s+/g, ' '));
    });
    var pager = document.createElement('nav');
    pager.className = 'pager';
    pager.setAttribute('aria-label', 'Pages of the collection');
    list.parentNode.insertBefore(pager, list.nextSibling);
    var state = { category: '', page: 1, query: '' };
    var address = function () {
      var q = new URLSearchParams();
      if (state.query) q.set('q', state.query);
      if (state.category) q.set('category', state.category);
      if (state.page > 1) q.set('page', state.page);
      var search = q.toString();
      history.replaceState(null, '', (search ? '?' + search : location.pathname) + '#collection');
    };
    var button = function (label, page, current, name) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'pill';
      b.textContent = label;
      b.setAttribute('data-page', page);
      if (name) b.setAttribute('aria-label', name);
      if (current) b.setAttribute('aria-current', 'page');
      return b;
    };
    // what the screen reader hears: at once after a click, once the typing pauses for a search
    var later = null;
    var announce = function (text, wait) {
      clearTimeout(later);
      if (!status) return;
      if (wait) later = setTimeout(function () { status.textContent = text; }, 700);
      else status.textContent = text;
    };
    // shows the cards of the state; announcement is false, 'now' or 'later'
    var show = function (announcement) {
      var terms = fold(state.query).split(/\s+/).filter(Boolean);
      var counts = {}, found = 0, hits = [];
      cards.forEach(function (card, i) {
        var match = terms.every(function (t) { return words[i].indexOf(t) >= 0; });
        var category = card.getAttribute('data-category');
        if (match) {
          counts[category] = (counts[category] || 0) + 1;
          found += 1;
        }
        if (match && (!state.category || category === state.category)) hits.push(card);
        else card.hidden = true;
      });
      each('[data-filter]', function (a) {
        var category = a.getAttribute('data-filter');
        var count = a.querySelector('.count');
        if (count) count.textContent = category ? counts[category] || 0 : found;
        if (category === state.category) a.setAttribute('aria-current', 'true');
        else a.removeAttribute('aria-current');
      }, filters);
      var pages = Math.max(1, Math.ceil(hits.length / PER_PAGE));
      state.page = Math.min(Math.max(1, state.page), pages);
      hits.forEach(function (card, i) { card.hidden = Math.floor(i / PER_PAGE) + 1 !== state.page; });
      pager.textContent = '';
      pager.hidden = pages < 2;
      if (pages > 1) {
        if (state.page > 1) pager.appendChild(button('Previous', state.page - 1, false));
        for (var k = 1; k <= pages; k += 1) pager.appendChild(button(String(k), k, k === state.page, 'Page ' + k));
        if (state.page < pages) pager.appendChild(button('Next', state.page + 1, false));
      }
      if (noHits) noHits.hidden = hits.length > 0;
      if (clear) clear.hidden = !state.query;
      if (announcement) {
        announce((hits.length ? hits.length : 'No') + (hits.length === 1 ? ' poster' : ' posters') +
          (state.query ? ' found' : '') + (pages > 1 ? ', page ' + state.page + ' of ' + pages : ''),
          announcement === 'later');
      }
    };
    var reset = function (everything) {
      state.query = '';
      if (input) input.value = '';
      if (everything) state.category = '';
      state.page = 1;
      show('now');
      address();
    };
    // the filters are links to the pages of the categories: here they filter the page in place
    filters.addEventListener('click', function (e) {
      var b = e.target.closest('[data-filter]');
      if (!b || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      state.category = b.getAttribute('data-filter');
      state.page = 1;
      show('now');
      address();
    });
    pager.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      state.page = Number(b.getAttribute('data-page'));
      show('now');
      address();
      document.getElementById('collection').scrollIntoView();
      // the buttons of the pager are made anew: the focus goes to the top of the page now shown
      if (heading) heading.focus({ preventScroll: true });
    });
    if (input) {
      finder.hidden = false;
      input.addEventListener('input', function () {
        state.query = input.value.trim();
        state.page = 1;
        show('later');
        address();
      });
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && input.value) {
          e.preventDefault();
          reset(false);
        }
      });
      // a click on the field, around the input, is a click in it
      finder.querySelector('.search').addEventListener('click', function (e) {
        if (!e.target.closest('button, input')) input.focus();
      });
      clear.addEventListener('click', function () {
        reset(false);
        input.focus();
      });
    }
    if (noHits) {
      noHits.querySelector('[data-clear]').addEventListener('click', function () {
        reset(true);
        if (input) input.focus();
      });
    }
    var params = new URLSearchParams(location.search);
    var asked = params.get('category');
    var known = Array.prototype.some.call(filters.querySelectorAll('[data-filter]'), function (b) {
      return b.getAttribute('data-filter') === asked;
    });
    if (asked && known) state.category = asked;
    state.page = parseInt(params.get('page'), 10) || 1;
    state.query = (params.get('q') || '').trim();
    if (input) input.value = state.query;
    show(false);
  }

  // A poster page: the pills choose the theme of the preview and of the download buttons.
  // Until one is pressed, the theme shown follows the mode of the site (the CSS shows its buttons).
  function posterThemes() {
    var poster = document.querySelector('[data-poster]');
    if (!poster) return;
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
  // request) on a canvas of the size chosen, This screen being that of the screen in device pixels,
  // filled with the paper colour of the theme, the poster centred and as large as a margin allows.
  // Nothing is sent anywhere: the PNG is made here. Only the PDF of the theme last asked for is kept,
  // and every canvas is emptied once used, so that a phone that makes several does not run out of
  // the memory its browser gives to canvases.
  function wallpaper() {
    var wall = document.querySelector('[data-wallpaper]');
    if (!wall || !window.HTMLCanvasElement || !window.Promise || !window.URL) return;
    var MAX_PIXELS = 16777216;  // the largest canvas that Safari draws on iOS
    var form = wall.querySelector('.wp-form');
    var status = wall.querySelector('.wp-status');
    var result = wall.querySelector('.wp-result');
    var button = form.querySelector('button[type=submit]');
    var lib = null, docs = {}, blobUrl = null, busy = false;
    var screenSize = form.querySelector('input[data-screen]');
    if (screenSize && window.screen && screen.width && screen.height) {
      var ratio = window.devicePixelRatio || 1;
      var w = Math.round(screen.width * ratio), h = Math.round(screen.height * ratio);
      var fit = Math.min(1, Math.sqrt(MAX_PIXELS / (w * h)));
      w = Math.floor(w * fit);
      h = Math.floor(h * fit);
      screenSize.setAttribute('data-w', w);
      screenSize.setAttribute('data-h', h);
      screenSize.parentNode.querySelector('.count').textContent = w + '\u00a0\u00d7\u00a0' + h;
      screenSize.parentNode.hidden = false;
      screenSize.checked = true;
    }
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
    // An error says what failed: loading the PDF (the connection), or drawing it (pdf.js needs a
    // recent browser, Promise.try and Math.sumPrecise for instance, and an older one fails there)
    var failed = function (what) {
      return function (e) { throw { what: what, error: e }; };
    };
    var load = function (url) {
      Object.keys(docs).forEach(function (other) {
        if (other === url) return;
        docs[other].then(function (doc) { doc.loadingTask.destroy(); }, function () { /* it never loaded */ });
        delete docs[other];
      });
      if (!docs[url]) {
        // cache: reload, since a PDF opened from its button may be in the cache of the browser
        // without the Access-Control-Allow-Origin header, which the bucket only sends to a request
        // from the site: taken from there, it would be refused to this script
        docs[url] = Promise.all([pdfjs().catch(failed('draw')), fetch(url, { cache: 'reload' }).then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.arrayBuffer();
        }).catch(failed('load'))]).then(function (both) {
          return both[0].getDocument({ data: new Uint8Array(both[1]), isEvalSupported: false }).promise
            .catch(failed('draw'));
        });
        docs[url].catch(function () { delete docs[url]; });
      }
      return docs[url];
    };
    var picked = function (name) { return form.querySelector('input[name=' + name + ']:checked'); };
    var say = function (text) { status.textContent = text; };
    form.hidden = false;
    form.addEventListener('change', function () { result.hidden = true; say(''); });
    // counted here rather than with data-umami-event, whose handler would open the PNG in place
    // of downloading it: Umami follows a link itself, which drops its download attribute
    var made = null;
    result.querySelector('a').addEventListener('click', function () {
      if (made) track('wallpaper-download', made);
    });
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
          background: paper }).promise.then(function () {
          page.cleanup();
          return sheet;
        });
      }).then(function (sheet) {
        var canvas = document.createElement('canvas');
        canvas.width = W;
        canvas.height = H;
        var ctx = canvas.getContext('2d');
        ctx.fillStyle = paper;
        ctx.fillRect(0, 0, W, H);
        ctx.drawImage(sheet, Math.round((W - sheet.width) / 2), Math.round((H - sheet.height) / 2));
        sheet.width = sheet.height = 0;
        return new Promise(function (resolve, reject) {
          canvas.toBlob(function (b) {
            canvas.width = canvas.height = 0;
            if (b) resolve(b); else reject(new Error('toBlob'));
          }, 'image/png');
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
        made = { slug: wall.getAttribute('data-slug'), screen: size.value, theme: theme.value };
        a.textContent = 'Download the PNG \u00b7 ' + (blob.size / 1e6).toFixed(1) + ' MB';
        result.hidden = false;
        say('Ready: ' + W + '\u00a0\u00d7\u00a0' + H + ' pixels.');
        track('wallpaper', { slug: wall.getAttribute('data-slug'), screen: size.value, theme: theme.value });
      }).catch(function (err) {
        say(err && err.what === 'load'
          ? 'The poster could not be loaded. Check the connection, or download the PDF above.'
          : 'This browser could not draw the wallpaper: an up-to-date one can, or download the PDF above.');
      }).then(function () {
        busy = false;
        button.disabled = false;
      });
    });
  }

  // The print guide, opened from the Print it button of a poster (?poster=<slug>&theme=<theme>):
  // a box with the Print from of that poster, a theme to choose and the links to its PDFs.
  function printGuide() {
    var box = document.getElementById('for-poster');
    var dataEl = document.getElementById('print-data');
    if (!box || !dataEl) return;
    var params = new URLSearchParams(location.search);
    var printData = null;
    try { printData = JSON.parse(dataEl.textContent); } catch (e) { /* the guide shows on its own */ }
    var slug = params.get('poster');
    var info = printData && Object.prototype.hasOwnProperty.call(printData.posters, slug) ? printData.posters[slug] : null;
    if (!info) return;
    var name = info[0], category = info[1], min = info[2], themes = info[3], version = info[4], lang = info[5];
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
    if (lang !== 'en') posterLink.lang = lang;
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
        a.href = printData.pdf.replace('{category}', category).replace('{file}', slug + '-' + f[0] + '-' + theme + '.pdf') +
          '?v=' + version;
        a.type = 'application/pdf';
        a.setAttribute('data-umami-event', 'download');
        a.setAttribute('data-umami-event-slug', slug);
        a.setAttribute('data-umami-event-format', f[0]);
        a.setAttribute('data-umami-event-theme', theme);
        a.target = '_blank';
        a.rel = 'noopener';
        li.appendChild(a);
        li.appendChild(make('span', 'fp-what', f[0] === 'A' ? 'Any ISO A size; body at 8 pt or more at ' + sizes.join(', ') : 'Its own layout'));
        files.appendChild(li);
      });
      var li = make('li');
      var a = make('a', 'btn btn-line', 'US formats, zip');
      a.href = printData.us.replace('{category}', category);
      a.setAttribute('data-umami-event', 'download-zip');
      a.setAttribute('data-umami-event-category', category + '-us');
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

  // An annotated reading page: the notes in the margin of a wide screen, pushed down so that none
  // covers the one above it, and a button to hide them, remembered. Without this script, or on a
  // small screen, the number after each marked phrase opens its note in the text.
  function marginNotes() {
    var annotated = document.querySelector('.annotated');
    if (!annotated) return;
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
        track('notes-toggle', { slug: textEl.getAttribute('data-paper'), shown: String(!off) });
        try { localStorage.setItem(NOTES, off ? 'off' : 'on'); } catch (e) { /* lasts for this page */ }
      });
    }
    // a note opened by its number, on a small screen or without the margin
    each('.sn-toggle', function (box) {
      box.addEventListener('change', function () {
        if (box.checked) track('margin-note', { slug: textEl.getAttribute('data-paper'), note: box.id.slice(4) });
      });
    }, annotated);
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
  function teachingKit() {
    var kit = document.querySelector('[data-teach]');
    if (!kit || !window.print) return;
    var PRINT_MODES = ['print-no-answers', 'print-answers-only'];
    var clear = function () { PRINT_MODES.forEach(function (c) { root.classList.remove(c); }); };
    window.addEventListener('afterprint', clear);
    each('[data-print]', function (b) {
      b.addEventListener('click', function () {
        clear();
        var how = b.getAttribute('data-print');
        if (how !== 'all') root.classList.add('print-' + how);
        track('teach-print', { slug: kit.getAttribute('data-slug'), mode: how });
        window.print();
      });
    }, kit);
    kit.querySelector('.teach-print').hidden = false;
  }

  // The blocks of a reading page or a teaching kit that scroll sideways on a narrow screen
  // (equations, figures, tables, code) take the focus of the keyboard while they scroll, so that
  // the arrow keys reach what they hide; a block without a role of its own gets one, and a name.
  function scrollables() {
    var main = document.querySelector('.text, .teach');
    if (!main) return;
    var BLOCKS = 'pre, .eq, .fm, figure, table, .table-wrap, .dump, .ascii, .key, .entry';
    var name = function (e) {
      return (e.matches('pre, .dump') ? 'Code' : e.matches('.eq, .fm') ? 'Equation' : 'Table') + ', scrolls sideways';
    };
    var mark = function () {
      each(BLOCKS, function (e) {
        var scrolls = e.scrollWidth > e.clientWidth + 1 && /auto|scroll/.test(getComputedStyle(e).overflowX);
        if (scrolls && !e.hasAttribute('tabindex')) {
          e.setAttribute('tabindex', '0');
          e.setAttribute('data-scrolls', '');
          if (!e.matches('figure, table')) {
            e.setAttribute('role', 'group');
            e.setAttribute('aria-label', name(e));
          }
        } else if (!scrolls && e.hasAttribute('data-scrolls')) {
          e.removeAttribute('tabindex');
          e.removeAttribute('data-scrolls');
          if (!e.matches('figure, table')) {
            e.removeAttribute('role');
            e.removeAttribute('aria-label');
          }
        }
      }, main);
    };
    var pending = false;
    var later = function () {
      if (pending) return;
      pending = true;
      requestAnimationFrame(function () { pending = false; mark(); });
    };
    mark();
    window.addEventListener('load', later);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(later);
    if (window.ResizeObserver) new ResizeObserver(later).observe(main);
    else window.addEventListener('resize', later);
  }

  // The images of a poster page and of a reading page open large on a click: the preview at its
  // largest width, a figure at the size of its file. A click on the large image shows it at full
  // size, to scroll; Escape, the close button or a click beside it closes it.
  function zoom() {
    var zoomable = document.querySelectorAll('.wall picture img, .text figure.image img');
    if (!zoomable.length || !window.HTMLDialogElement) return;
    var dialog = document.createElement('dialog');
    dialog.className = 'zoom';
    dialog.innerHTML = '<button type="button" class="zoom-close" aria-label="Close">\u00d7</button><img alt="">';
    document.body.appendChild(dialog);
    var big = dialog.querySelector('img');
    var close = function () { dialog.close(); };
    dialog.addEventListener('close', function () { dialog.classList.remove('full'); big.removeAttribute('src'); });
    dialog.addEventListener('click', function (e) {
      if (e.target === big) dialog.classList.toggle('full');
      else if (e.target === dialog) close();
    });
    dialog.querySelector('.zoom-close').addEventListener('click', close);
    Array.prototype.forEach.call(zoomable, function (img) {
      img.classList.add('zoomable');
      img.tabIndex = 0;
      img.setAttribute('role', 'button');
      img.setAttribute('aria-label', 'Enlarge: ' + img.alt);
      var open = function () {
        var src = img.currentSrc || img.src;
        // a preview: its largest width, in the theme shown
        if (img.closest('.wall')) src = src.replace(/-600(\.\w+)$/, '-1200$1');
        var look = getComputedStyle(img);
        big.style.filter = look.filter;
        big.style.backgroundColor = look.backgroundColor;
        big.alt = img.alt;
        big.src = src;
        dialog.showModal();
      };
      img.addEventListener('click', open);
      img.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
      });
    });
  }

  themeButton();
  menu();
  collection();
  posterThemes();
  wallpaper();
  printGuide();
  marginNotes();
  teachingKit();
  scrollables();
  zoom();
  apply(mode());
})();
