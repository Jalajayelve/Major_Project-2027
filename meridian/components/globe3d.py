"""3D globe (Three.js, lazy-loaded from assets/scene.js) with an SVG fallback.

Modes (data-globe):
  dash    dashboard globe: slow spin, drag to rotate, follows the selected university
  agents  agents page: slow spin, routes appear as agents complete
  band    landing band: rotation follows scroll
  hero    desk scene: mouse tilt only (no spin)
"""
import json

import reflex as rx

from ..data import mock


def unis_json() -> str:
    return json.dumps([{"id": u["id"], "lat": u["lat"], "lon": u["lon"]} for u in mock.UNIVERSITIES])


def fallback_svg(dark_surface: bool = False) -> str:
    stroke = "var(--ivory)" if dark_surface else "var(--slate)"
    fill_a, fill_b = ("var(--navy-2)", "var(--navy)") if dark_surface else ("var(--navy)", "var(--navy)")
    meridians = "".join(
        f'<ellipse class="m" style="animation-delay:-{i * 1.9}s" cx="100" cy="100" rx="{r}" ry="92" fill="none" stroke="{stroke}" stroke-width=".8" opacity=".55"/>'
        for i, r in enumerate((30, 62, 88))
    )
    parallels = "".join(
        f'<ellipse cx="100" cy="{y}" rx="{w}" ry="{h}" fill="none" stroke="{stroke}" stroke-width=".7" opacity=".4"/>'
        for y, w, h in ((100, 92, 12), (62, 78, 9), (138, 78, 9), (30, 44, 5), (170, 44, 5))
    )
    return (
        '<svg viewBox="0 0 200 200" width="100%" height="100%" aria-hidden="true">'
        f'<defs><radialGradient id="gl{int(dark_surface)}" cx="32%" cy="26%" r="80%"><stop offset="0" stop-color="{fill_a}" stop-opacity=".85"/><stop offset="1" stop-color="{fill_b}"/></radialGradient></defs>'
        f'<circle cx="100" cy="100" r="94" fill="url(#gl{int(dark_surface)})"/>{meridians}{parallels}'
        '<path class="rt" d="M58 118 Q84 40 138 62" fill="none" stroke="var(--accent)" stroke-width="2"/>'
        '<circle cx="58" cy="118" r="3.2" fill="var(--ivory)"/><circle cx="138" cy="62" r="4" fill="var(--accent)" stroke="var(--ivory)" stroke-width="1.5"/></svg>'
    )


def globe3d(mode: str, class_name: str = "", spin: str = "auto", arcs: str = "all", select: bool = False,
            drag: bool = False, dark_surface: bool = False, destinations: list[dict] | None = None, **kw):
    return rx.el.div(
        rx.el.div(rx.html(fallback_svg(dark_surface)), class_name="globe-fallback"),
        rx.el.canvas(custom_attrs={
            "data-globe": mode, "data-unis": unis_json() if destinations is None else json.dumps(destinations), "data-arcs": arcs, "data-spin": spin,
            "data-select": "1" if select else "0", "data-drag": "1" if drag else "0",
        }),
        class_name=f"globe3d {class_name}".strip(), **kw,
    )
