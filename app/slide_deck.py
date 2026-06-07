"""Generic presentation slide-deck: layout, navigation, and optional architecture sub-steps."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dash import Input, Output, State, callback, clientside_callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

import presentation as pres


@dataclass(frozen=True)
class Slide:
    """One deck slide: header copy plus body content."""

    title: str
    subtitle: str
    body: html.Div
    body_class: str = "slide-body"


@dataclass(frozen=True)
class ArchitectureOverlay:
    """
    Optional interactive sub-steps on a single slide (e.g. progressive architecture reveal).

    `build_diagram` returns the diagram root; the overlay sets `data-arch-step` on the wrapper.
    """

    step_titles: tuple[str, ...]
    build_diagram: Callable[[], html.Div]
    slide_index: int | None = None
    wrapper_class: str = "slide-arch-wrap dip-arch-root"
    body_class: str = "slide-body slide-body-arch"
    counter_slide_number: int | None = None


@dataclass(frozen=True)
class SlideDeckConfig:
    """Configuration for a full presentation page."""

    deck_id: str
    slides: tuple[Slide, ...]
    kicker: str = "Solution overview"
    page_class: str = "page-slide-deck"
    architecture: ArchitectureOverlay | None = None


def _arch_slide_index(config: SlideDeckConfig) -> int | None:
    if config.architecture is None:
        return None
    if config.architecture.slide_index is not None:
        return config.architecture.slide_index
    return len(config.slides) - 1


def _arch_step_count(config: SlideDeckConfig) -> int:
    if config.architecture is None:
        return 0
    return len(config.architecture.step_titles)


def _architecture_body(config: SlideDeckConfig, arch_step: int) -> html.Div:
    overlay = config.architecture
    assert overlay is not None
    deck_id = config.deck_id
    return html.Div(
        id=f"{deck_id}-arch-root",
        className=overlay.wrapper_class,
        **{"data-arch-step": str(arch_step)},
        children=[
            overlay.build_diagram(),
            html.Div(id=f"{deck_id}-arch-sync", style={"display": "none"}),
        ],
    )


def slide_at(config: SlideDeckConfig, index: int, arch_step: int = 1) -> html.Div:
    slide = config.slides[index]
    title = slide.title
    subtitle = slide.subtitle
    body = slide.body
    body_class = slide.body_class

    arch_index = _arch_slide_index(config)
    if arch_index is not None and index == arch_index and config.architecture is not None:
        overlay = config.architecture
        subtitle = overlay.step_titles[arch_step - 1]
        body_class = overlay.body_class
        body = _architecture_body(config, arch_step)

    return pres.slide_panel(
        title,
        subtitle,
        body,
        body_class=body_class,
        subtitle_id=f"{config.deck_id}-slide-subtitle",
    )


def _slide_subtitle(config: SlideDeckConfig, index: int, arch_step: int) -> str:
    arch_index = _arch_slide_index(config)
    if arch_index is not None and index == arch_index and config.architecture is not None:
        return config.architecture.step_titles[arch_step - 1]
    return config.slides[index].subtitle


def deck_counter(config: SlideDeckConfig, index: int, arch_step: int) -> str:
    arch_index = _arch_slide_index(config)
    if arch_index is not None and index == arch_index and config.architecture is not None:
        slide_num = config.architecture.counter_slide_number or (index + 1)
        return f"{slide_num} · Step {arch_step} / {_arch_step_count(config)}"
    return f"{index + 1} / {len(config.slides)}"


def deck_progress(config: SlideDeckConfig, index: int, arch_step: int) -> dict[str, str]:
    slide_count = len(config.slides)
    arch_index = _arch_slide_index(config)
    if arch_index is not None and index == arch_index and config.architecture is not None:
        arch_steps = _arch_step_count(config)
        width = ((slide_count - 1 + arch_step / arch_steps) / slide_count) * 100
    else:
        width = ((index + 1) / slide_count) * 100
    return {"width": f"{width:.2f}%"}


def deck_dots(config: SlideDeckConfig, index: int) -> list[html.Span]:
    return [
        html.Span(className="slide-dot" + (" slide-dot-active" if i == index else ""))
        for i in range(len(config.slides))
    ]


def build_page_layout(config: SlideDeckConfig) -> html.Div:
    """Page wrapper with optional architecture step store and deck shell."""
    slide_count = len(config.slides)
    stores: list = []
    if config.architecture is not None:
        stores.append(dcc.Store(id=f"{config.deck_id}-arch-step", data=1))

    return html.Div(
        className=config.page_class,
        children=[
            *stores,
            pres.slide_deck(
                config.deck_id,
                subtitle=config.kicker,
                slide_count=slide_count,
                initial_viewport=slide_at(config, 0, 1),
                initial_counter=deck_counter(config, 0, 1),
                initial_dots=deck_dots(config, 0),
            ),
        ],
    )


def register_slide_deck(config: SlideDeckConfig) -> None:
    """Register prev/next navigation callback for a deck configuration."""
    deck_id = config.deck_id
    slide_count = len(config.slides)
    arch_index = _arch_slide_index(config)
    arch_steps = _arch_step_count(config)

    outputs = [
        Output(f"{deck_id}-viewport", "children"),
        Output(f"{deck_id}-slide-subtitle", "children"),
        Output(f"{deck_id}-counter", "children"),
        Output(f"{deck_id}-dots", "children"),
        Output(f"{deck_id}-prev", "className"),
        Output(f"{deck_id}-next", "className"),
        Output(f"{deck_id}-progress", "style"),
        Output(f"{deck_id}-index", "data"),
    ]
    states = [
        State(f"{deck_id}-index", "data"),
    ]
    if config.architecture is not None:
        outputs.append(Output(f"{deck_id}-arch-step", "data"))
        states.append(State(f"{deck_id}-arch-step", "data"))

    @callback(
        *outputs,
        Input(f"{deck_id}-prev", "n_clicks"),
        Input(f"{deck_id}-next", "n_clicks"),
        *states,
        prevent_initial_call=True,
    )
    def _sync_deck(prev_clicks, next_clicks, stored_idx, stored_arch_step=None):
        from dash import ctx

        if ctx.triggered_id not in (f"{deck_id}-prev", f"{deck_id}-next"):
            raise PreventUpdate

        idx = int(stored_idx or 0)
        arch_step = int(stored_arch_step or 1) if config.architecture is not None else 1

        if ctx.triggered_id == f"{deck_id}-prev":
            if arch_index is not None and idx == arch_index and arch_step > 1:
                arch_step -= 1
            else:
                if arch_index is not None and idx == arch_index:
                    arch_step = 1
                idx = max(0, idx - 1)
        else:
            if arch_index is not None and idx == arch_index:
                if arch_step < arch_steps:
                    arch_step += 1
                else:
                    raise PreventUpdate
            else:
                idx = min(slide_count - 1, idx + 1)
                if arch_index is not None and idx == arch_index:
                    arch_step = 1

        on_arch = arch_index is not None and idx == arch_index
        prev_enabled = idx > 0 or (on_arch and arch_step > 1)
        next_enabled = not on_arch or arch_step < arch_steps
        prev_cls = "slide-deck-btn" if prev_enabled else "slide-deck-btn slide-deck-btn-disabled"
        next_cls = "slide-deck-btn" if next_enabled else "slide-deck-btn slide-deck-btn-disabled"

        stored_idx_int = int(stored_idx or 0)
        only_arch_step = (
            arch_index is not None
            and idx == arch_index
            and idx == stored_idx_int
            and arch_step != int(stored_arch_step or 1)
        )
        viewport_out = no_update if only_arch_step else slide_at(config, idx, arch_step)

        result = (
            viewport_out,
            _slide_subtitle(config, idx, arch_step),
            deck_counter(config, idx, arch_step),
            deck_dots(config, idx),
            prev_cls,
            next_cls,
            deck_progress(config, idx, arch_step),
            idx,
        )
        if config.architecture is not None:
            result = (*result, arch_step)
        return result

    if config.architecture is not None:

        clientside_callback(
            f"""
            function(step) {{
                const el = document.getElementById("{deck_id}-arch-root");
                if (el && step != null) {{
                    el.setAttribute("data-arch-step", String(step));
                }}
                return window.dash_clientside.no_update;
            }}
            """,
            Output(f"{deck_id}-arch-sync", "children"),
            Input(f"{deck_id}-arch-step", "data"),
        )
