/**
 * Arrow-key navigation for presentation slide decks (.slide-deck).
 * Left / Right arrows click prev/next when the deck is on screen.
 */
(function () {
  if (window.__energyTradingSlideDeckKeys) return;
  window.__energyTradingSlideDeckKeys = true;

  function isDisabled(btn) {
    return btn.classList.contains("slide-deck-btn-disabled");
  }

  function isEditableTarget(target) {
    if (!target || !target.tagName) return false;
    const tag = target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    return target.isContentEditable;
  }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    if (isEditableTarget(e.target)) return;

    const deck = document.querySelector(".slide-deck");
    if (!deck) return;

    const prev = deck.querySelector('[id$="-prev"]');
    const next = deck.querySelector('[id$="-next"]');
    if (!prev && !next) return;

    if (e.key === "ArrowLeft" && prev && !isDisabled(prev)) {
      e.preventDefault();
      prev.click();
    } else if (e.key === "ArrowRight" && next && !isDisabled(next)) {
      e.preventDefault();
      next.click();
    }
  });
})();
