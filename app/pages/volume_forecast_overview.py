"""Volume forecasting — Overview & Architecture (presentation deck)."""

from __future__ import annotations

import dash

from decks.volume_forecast import CONFIG
from slide_deck import build_page_layout, register_slide_deck

dash.register_page(
    __name__,
    path="/volume-forecasting/overview",
    name="Volume Forecast Overview",
    title="Overview — Volume forecasting",
)

register_slide_deck(CONFIG)


def layout():
    return build_page_layout(CONFIG)
