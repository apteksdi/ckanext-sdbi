(function () {
  var CLOSE_MS = 320;

  function bindHoverDropdown(root) {
    var timer = null;
    var toggle =
      root.querySelector(':scope > .dropdown-toggle') ||
      root.querySelector('.dropdown-toggle');

    function open() {
      if (timer) {
        window.clearTimeout(timer);
        timer = null;
      }
      root.classList.add('open');
      if (toggle) toggle.setAttribute('aria-expanded', 'true');
    }

    function scheduleClose() {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        root.classList.remove('open');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
        timer = null;
      }, CLOSE_MS);
    }

    root.addEventListener('mouseenter', open);
    root.addEventListener('mouseleave', scheduleClose);
    root.addEventListener('focusin', open);
    root.addEventListener('focusout', function (e) {
      if (!root.contains(e.relatedTarget)) scheduleClose();
    });

    // Keep open while pointer is on the menu (absolute, may sit outside li box).
    var menu = root.querySelector(':scope > .dropdown-menu');
    if (menu) {
      menu.addEventListener('mouseenter', open);
      menu.addEventListener('mouseleave', scheduleClose);
    }
  }

  function init() {
    var items = document.querySelectorAll(
      '.site-header .navigation li.dropdown, .site-header__user.dropdown'
    );
    Array.prototype.forEach.call(items, bindHoverDropdown);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
