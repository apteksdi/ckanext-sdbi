(function () {
  'use strict';

  var burger = document.querySelector('.sdbi-home .sdbi-home-burger');
  var nav = document.querySelector('.sdbi-home .sdbi-home-nav');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.querySelector('.sdbi-home').addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) {
        nav.classList.remove('is-open');
        burger.setAttribute('aria-expanded', 'false');
        burger.focus();
      }
    });
  }
})();
