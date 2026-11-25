/* CKAN api-info.js initializes BS5 Modal with .modal() but never calls
 * .modal('show'). Patch click handling so the Data API dialog opens. */
(function ($) {
  function showLatest() {
    var $modal = $('.sdbi-api-info-modal').last();
    if (!$modal.length || $modal.hasClass('show')) {
      return;
    }
    $modal.modal('show');
  }

  $(document).on('click', '[data-module="api-info"]', function () {
    // loadTemplate is async; retry briefly until the snippet is in the DOM.
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      if ($('.sdbi-api-info-modal').length) {
        clearInterval(timer);
        showLatest();
      } else if (tries >= 40) {
        clearInterval(timer);
      }
    }, 50);
  });
})(window.jQuery);
