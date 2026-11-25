(function () {
  function init() {
    var root = document.getElementById('site-header-search');
    if (!root) return;

    var toggle = document.getElementById('site-header-search-toggle');
    var panel = document.getElementById('site-header-search-panel');
    var closeBtn = document.getElementById('site-header-search-close');
    var input = document.getElementById('field-sitewide-search');
    if (!toggle || !panel) return;

    function openSearch() {
      root.classList.add('is-open');
      panel.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
      if (input) {
        window.setTimeout(function () { input.focus(); }, 0);
      }
    }

    function closeSearch() {
      root.classList.remove('is-open');
      panel.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
    }

    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (root.classList.contains('is-open')) {
        closeSearch();
      } else {
        openSearch();
      }
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.preventDefault();
        closeSearch();
        toggle.focus();
      });
    }

    document.addEventListener('click', function (e) {
      if (!root.classList.contains('is-open')) return;
      if (!root.contains(e.target)) closeSearch();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && root.classList.contains('is-open')) {
        closeSearch();
        toggle.focus();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
