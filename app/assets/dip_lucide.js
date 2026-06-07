/**
 * Initialise Lucide icons app-wide; re-run when Dash updates the DOM.
 */
(function () {
  if (window.__energyTradingDipLucide) return;
  window.__energyTradingDipLucide = true;

  var timer = null;

  function refreshLucide() {
    if (typeof lucide === "undefined" || !lucide.createIcons) return;
    lucide.createIcons({
      attrs: {
        "stroke-width": 2,
        "aria-hidden": "true",
      },
    });
  }

  function scheduleRefresh() {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(refreshLucide, 50);
  }

  document.addEventListener("DOMContentLoaded", function () {
    scheduleRefresh();
    if (document.body) {
      var observer = new MutationObserver(scheduleRefresh);
      observer.observe(document.body, { childList: true, subtree: true });
    }
  });
})();
