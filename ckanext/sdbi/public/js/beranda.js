/* Beranda SDBI
   1. Gentle reveal-on-scroll + one-time count-up (skipped for reduced motion).
   2. Hero search autocomplete (always on; plain form submit still works without JS).
   3. Interactive how-to tour.  4. Provider type filter. */
(function () {
  'use strict';
  var root = document.querySelector('.sdbi-home');
  if (!root) return;

  function formatDot(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  /* ---------- 1. Motion ---------- */
  function initMotion() {
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce || !('IntersectionObserver' in window)) return;
    root.classList.add('sdbi-home-motion');

    function countUp(el) {
      var target = parseInt(el.getAttribute('data-count'), 10);
      if (!target || target < 1) return;
      var duration = 1400;
      var start = null;
      el.textContent = '0';
      function step(ts) {
        if (start === null) start = ts;
        var t = Math.min((ts - start) / duration, 1);
        var eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
        el.textContent = formatDot(Math.round(target * eased));
        if (t < 1) window.requestAnimationFrame(step);
      }
      window.requestAnimationFrame(step);
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        io.unobserve(el);
        if (el.hasAttribute('data-count')) countUp(el);
        else el.classList.add('is-visible');
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    root.querySelectorAll('[data-reveal], [data-count]').forEach(function (el) { io.observe(el); });
  }

  /* ---------- 2. Search autocomplete ---------- */
  function initAutocomplete() {
    var form = root.querySelector('.sdbi-home-hero-search[data-autocomplete]');
    if (!form || !window.fetch) return;
    var input = form.querySelector('input[name="q"]');
    var list = form.querySelector('#sdbi-home-suggest');
    var endpoint = form.getAttribute('data-autocomplete');
    var datasetUrl = form.getAttribute('data-dataset-url');
    var timer = null;
    var seq = 0;
    var active = -1;

    function options() { return list.querySelectorAll('li[role="option"]'); }

    function close() {
      list.hidden = true;
      list.innerHTML = '';
      active = -1;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
    }

    function highlight(index) {
      var opts = options();
      if (!opts.length) return;
      active = (index + opts.length) % opts.length;
      opts.forEach(function (li, i) { li.setAttribute('aria-selected', i === active ? 'true' : 'false'); });
      input.setAttribute('aria-activedescendant', opts[active].id);
      opts[active].scrollIntoView({ block: 'nearest' });
    }

    function option(id, href, iconClass, text) {
      var li = document.createElement('li');
      li.id = id;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', 'false');
      var a = document.createElement('a');
      a.href = href;
      a.tabIndex = -1;
      var icon = document.createElement('i');
      icon.className = 'fa ' + iconClass;
      icon.setAttribute('aria-hidden', 'true');
      a.appendChild(icon);
      a.appendChild(document.createTextNode(' ' + text)); // textContent only: titles are user data
      li.appendChild(a);
      return li;
    }

    function render(query, results) {
      list.innerHTML = '';
      results.forEach(function (r, i) {
        list.appendChild(option('sdbi-home-suggest-' + i,
          datasetUrl.replace('__name__', encodeURIComponent(r.name)),
          'fa-database', r.title || r.name));
      });
      if (!results.length) {
        var empty = document.createElement('li');
        empty.className = 'sdbi-home-suggest-empty';
        empty.textContent = 'Tidak ada judul yang cocok. Tekan Enter untuk mencari di semua isi dataset.';
        list.appendChild(empty);
      }
      var all = option('sdbi-home-suggest-all',
        form.getAttribute('action') + '?q=' + encodeURIComponent(query),
        'fa-magnifying-glass', 'Cari "' + query + '" di semua dataset');
      all.classList.add('sdbi-home-suggest-all');
      list.appendChild(all);
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      active = -1;
    }

    function lookup() {
      var query = input.value.trim();
      if (query.length < 2) { close(); return; }
      var mine = ++seq;
      fetch(endpoint + '?limit=6&incomplete=' + encodeURIComponent(query), { headers: { Accept: 'application/json' } })
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (data) {
          if (mine !== seq || !data) return; // a newer keystroke won
          var results = (data.ResultSet && data.ResultSet.Result) || [];
          render(query, results);
        })
        .catch(function () { /* network error: keep plain search working */ });
    }

    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(lookup, 220);
    });
    input.addEventListener('keydown', function (e) {
      if (list.hidden) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); highlight(active + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); highlight(active - 1); }
      else if (e.key === 'Escape') { close(); }
      else if (e.key === 'Enter' && active >= 0) {
        e.preventDefault();
        window.location.href = options()[active].querySelector('a').href;
      }
    });
    document.addEventListener('click', function (e) { if (!form.contains(e.target)) close(); });
    input.addEventListener('blur', function () { setTimeout(function () { if (!form.contains(document.activeElement)) close(); }, 150); });
  }

  /* ---------- 3. Tur "Cara memakai portal" ---------- */
  function initTour() {
    var tour = root.querySelector('[data-tour]');
    if (!tour) return;
    var tabs = Array.prototype.slice.call(tour.querySelectorAll('[role="tab"]'));
    var panels = tabs.map(function (t) { return document.getElementById(t.getAttribute('aria-controls')); });
    if (!tabs.length || panels.indexOf(null) !== -1) return;

    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var STEP_MS = 7000;
    var current = 0;
    var timer = null;
    var stopped = reduce;   // the visitor took control (or prefers no motion)
    var visible = false;
    var typingTimer = null;

    tour.classList.add('is-tabbed');

    function progressOf(i) { return tabs[i].querySelector('.sdbi-home-tour-progress span'); }

    function resetProgress() {
      tabs.forEach(function (t, i) {
        var bar = progressOf(i);
        if (!bar) return;
        bar.style.transition = 'none';
        bar.style.width = '0';
      });
    }

    function runProgress() {
      var bar = progressOf(current);
      if (!bar || stopped) return;
      void bar.offsetWidth; // restart the transition
      bar.style.transition = 'width ' + STEP_MS + 'ms linear';
      bar.style.width = '100%';
    }

    function typeQuery(panel) {
      var el = panel.querySelector('[data-type-text]');
      if (!el) return;
      var text = el.getAttribute('data-type-text');
      clearTimeout(typingTimer);
      if (reduce) { el.textContent = text; return; }
      var i = 0;
      el.textContent = '';
      (function next() {
        el.textContent = text.slice(0, ++i);
        if (i < text.length) typingTimer = setTimeout(next, 110);
      })();
    }

    function schedule() {
      clearTimeout(timer);
      if (stopped || !visible) return;
      runProgress();
      timer = setTimeout(function () { select((current + 1) % tabs.length, false); }, STEP_MS);
    }

    function select(i, byUser) {
      current = i;
      tabs.forEach(function (t, j) {
        var on = j === i;
        t.classList.toggle('is-active', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        panels[j].hidden = !on;
      });
      if (byUser) { stopped = true; clearTimeout(timer); }
      resetProgress();
      if (i === 0) typeQuery(panels[0]);
      schedule();
    }

    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(i, true); });
      t.addEventListener('keydown', function (e) {
        var to = null;
        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') to = (i + 1) % tabs.length;
        else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') to = (i - 1 + tabs.length) % tabs.length;
        else if (e.key === 'Home') to = 0;
        else if (e.key === 'End') to = tabs.length - 1;
        if (to === null) return;
        e.preventDefault();
        select(to, true);
        tabs[to].focus();
      });
    });

    // Pause while the pointer is over the tour; resume the current step after.
    tour.addEventListener('mouseenter', function () { clearTimeout(timer); resetProgress(); });
    tour.addEventListener('mouseleave', schedule);
    tour.addEventListener('focusin', function () { stopped = true; clearTimeout(timer); resetProgress(); });

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        if (visible) schedule(); else { clearTimeout(timer); resetProgress(); }
      }, { threshold: 0.35 }).observe(tour);
    }

    select(0, false);
    // enable panel transitions only after the first paint of the tabbed state
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () { tour.classList.add('is-ready'); });
    });
  }

  /* ---------- 4. Filter penyedia data ---------- */
  function initProviderFilter() {
    var bar = root.querySelector('[data-provider-filter]');
    if (!bar) return;
    var items = root.querySelectorAll('.sdbi-home-penyedia-list > li');
    bar.hidden = false;
    bar.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-type]');
      if (!btn) return;
      var type = btn.getAttribute('data-type');
      bar.querySelectorAll('button').forEach(function (b) {
        var on = b === btn;
        b.classList.toggle('is-active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      items.forEach(function (li) {
        li.hidden = type !== 'semua' && li.getAttribute('data-type') !== type;
      });
    });
  }

  initMotion();
  initAutocomplete();
  initTour();
  initProviderFilter();
})();
