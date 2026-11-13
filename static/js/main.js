/* Small progressive enhancements for the storefront and admin. */
(function () {
  "use strict";

  // Confirm any element with data-confirm before submitting.
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (event) {
      if (!window.confirm(el.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });

  // Auto-submit the variety filter only when a value is picked.
  document.querySelectorAll("select[data-auto-submit]").forEach(function (select) {
    select.addEventListener("change", function () {
      if (select.form) select.form.submit();
    });
  });

  // Keep the WhatsApp links on product cards honest about the current price.
  document.querySelectorAll(".card").forEach(function (card) {
    var link = card.querySelector("a.wa-btn");
    var name = card.querySelector("h3 a");
    if (link && name && !link.dataset.done) {
      link.dataset.done = "1";
    }
  });
})();
