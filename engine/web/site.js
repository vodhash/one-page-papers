/* one-page-papers: the theme button, the menu on small screens, the filters of the collection
   and the themes of a poster. Every page works without it: the colours follow the system, the
   whole collection shows, and a poster page offers the PDF of each theme. */
(function () {
  'use strict';
  var root = document.documentElement;
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

  apply(mode());
})();
