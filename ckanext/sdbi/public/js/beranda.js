/* Beranda SDBI: gentle reveal-on-scroll + one-time count-up for stats.
   Content is fully visible without JS; motion is opt-in via .sdbi-home-motion
   and skipped entirely for prefers-reduced-motion. */
(function () {
  'use strict';
  var root = document.querySelector('.sdbi-home');
  if (!root) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window)) return;

  root.classList.add('sdbi-home-motion');

  function formatDot(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function countUp(el) {
    var target = parseInt(el.getAttribute('data-count'), 10);
    if (!target || target < 1) return;
    var duration = 1400;
    var start = null;
    el.textContent = '0';
    function step(ts) {
      if (start === null) start = ts;
      var t = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - t, 3); // easeOutCubic: fast start, soft landing
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
      if (el.hasAttribute('data-count')) {
        countUp(el);
      } else {
        el.classList.add('is-visible');
      }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

  root.querySelectorAll('[data-reveal], [data-count]').forEach(function (el) {
    io.observe(el);
  });
})();
