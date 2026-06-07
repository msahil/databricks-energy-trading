"""Short-term trading — Overview & Architecture (presentation deck)."""

from __future__ import annotations

import dash

from decks.short_term import CONFIG
from slide_deck import build_page_layout, register_slide_deck

dash.register_page(
    __name__,
    path="/short-term/overview",
    name="Short-term Overview",
    title="Overview — Short-term trading",
)

register_slide_deck(CONFIG)


def layout():
    return build_page_layout(CONFIG)
