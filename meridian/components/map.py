"""Restrained US map: printed outline, graticule, route lines, selectable markers."""
import reflex as rx

from ..data import mock
from ..state import State

VB_W, VB_H = 1000, 560


def _xy(lon, lat):
    x, y = mock.project(lon, lat)
    return x / 100 * VB_W, y / 100 * VB_H


def _base_svg() -> str:
    grid = []
    for lon in range(-125, -65, 5):
        x, _ = _xy(lon, 0)
        grid.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{VB_H}"/>')
    for lat in range(25, 51, 5):
        _, y = _xy(0, lat)
        grid.append(f'<line x1="0" y1="{y:.1f}" x2="{VB_W}" y2="{y:.1f}"/>')
    pts = " ".join(f"{_xy(lo, la)[0]:.1f},{_xy(lo, la)[1]:.1f}" for lo, la in mock.US_OUTLINE)
    return (
        f'<svg viewBox="0 0 {VB_W} {VB_H}" preserveAspectRatio="none" aria-hidden="true">'
        f'<g stroke="var(--rule)" stroke-width="1">{"".join(grid)}</g>'
        f'<polygon points="{pts}" fill="var(--ivory)" stroke="var(--ink)" stroke-width="1.4" stroke-linejoin="round"/>'
        f'<text x="{VB_W * .43:.0f}" y="{VB_H * .62:.0f}" font-family="IBM Plex Mono, monospace" font-size="15" letter-spacing="9" fill="var(--slate)" opacity=".8">UNITED STATES</text>'
        f'</svg>'
    )


def _route_svg(u) -> str:
    ox, oy = 18, 22  # arrival gateway (top-left)
    x, y = u["xf"] / 100 * VB_W, u["yf"] / 100 * VB_H
    cx, cy = (ox + x) / 2, min(oy, y) - 70
    return f'<svg viewBox="0 0 {VB_W} {VB_H}" preserveAspectRatio="none" aria-hidden="true"><path d="M{ox} {oy} Q{cx:.0f} {cy:.0f} {x:.1f} {y:.1f}"/></svg>'


def university_map():
    layers = [rx.el.div(rx.html(_base_svg()), class_name="map-layer")]
    for u in mock.UNIVERSITIES:
        sel = State.selected_uni == u["id"]
        layers.append(rx.el.div(rx.html(_route_svg(u)), class_name=rx.cond(sel, "map-layer route-line sel", "map-layer route-line"), style={"pointerEvents": "none"}))
    for u in mock.UNIVERSITIES:
        sel = State.selected_uni == u["id"]
        layers.append(rx.el.span(u["short"], class_name=rx.cond(sel, "map-label sel", "map-label"),
                                style={"left": u["x"], "top": u["y"], **({"transform": "translate(calc(-100% - 12px),-50%)"} if u["xf"] > 78 else {})}))
    for u in mock.UNIVERSITIES:
        sel = State.selected_uni == u["id"]
        layers.append(rx.el.button(
            on_click=State.select_uni(u["id"]), type="button", title=u["name"], aria_label=u["name"],
            class_name=rx.cond(sel, "marker sel", "marker"), style={"left": u["x"], "top": u["y"]},
        ))
    layers.append(rx.el.span("Arriving from India", class_name="mono origin", style={"fontSize": "9.5px"}))
    return rx.el.div(*layers, class_name="map-wrap")


def uni_chips():
    return rx.el.div(
        *[rx.el.button(u["short"], on_click=State.select_uni(u["id"]), type="button",
                       class_name=rx.cond(State.selected_uni == u["id"], "uni-chip sel", "uni-chip")) for u in mock.UNIVERSITIES],
        class_name="row wrap", style={"gap": "8px", "marginTop": "16px"},
    )


def uni_info_cards():
    from .common import label
    cards = []
    for u in mock.UNIVERSITIES:
        cards.append(rx.cond(
            State.selected_uni == u["id"],
            rx.el.div(
                rx.el.div(label(u["tier"], "blue"), label(u["city"]), class_name="row between"),
                rx.el.h3(u["name"], class_name="h3", style={"margin": "14px 0 4px", "fontSize": "26px"}),
                rx.el.p(u["program"], class_name="body"),
                rx.el.hr(class_name="rule", style={"margin": "20px 0"}),
                rx.el.div(
                    rx.el.div(label("Admission"), rx.el.p(u["prob_str"], class_name="num-key", style={"fontSize": "44px", "marginTop": "6px"})),
                    rx.el.div(label("Tuition / yr"), rx.el.p(u["tuition_str"], class_name="serif", style={"fontSize": "30px", "fontWeight": 600, "margin": "6px 0 0"})),
                    class_name="row between",
                ),
                rx.el.p(u["note"], class_name="body", style={"marginTop": "20px"}),
                rx.el.div(label("Deadline"), rx.el.span(u["deadline"], style={"fontWeight": 600, "marginLeft": "12px"}), class_name="row", style={"marginTop": "18px"}),
                class_name="info-card", key=u["id"],
            ),
            rx.fragment(),
        ))
    return rx.el.div(*cards)
