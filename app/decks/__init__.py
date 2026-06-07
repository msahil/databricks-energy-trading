"""
Domain-specific presentation decks.

Each module exports a ``SlideDeckConfig`` (e.g. ``decks.short_term.CONFIG``).
Register it from a thin ``app/pages/<name>_overview.py`` page:

    from decks.short_term import CONFIG  # or decks.volume_forecast.CONFIG
    from slide_deck import build_page_layout, register_slide_deck

    register_slide_deck(CONFIG)

    def layout():
        return build_page_layout(CONFIG)
"""
