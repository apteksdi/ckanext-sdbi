(function () {
  'use strict';

  var burger = document.querySelector('.sdbi-home .sdbi-home-burger');
  var nav = document.querySelector('.sdbi-home .sdbi-home-nav');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
})();
