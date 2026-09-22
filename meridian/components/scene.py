"""Landing hero scene: a photographed-desk composition.

Layers carry `data-depth`; /assets/scene.js moves them at different speeds on
mouse move and lazy-loads a Three.js globe into the canvas. Without JS, on
touch devices, or with prefers-reduced-motion, the static CSS/SVG scene shows.
"""
import reflex as rx

from .. import brand_assets as B
from ..data import mock
from .brand import monogram, wordmark
from .globe3d import unis_json


def _globe_fallback_svg() -> str:
    lines = "".join(
        f'<ellipse cx="100" cy="100" rx="{rx_}" ry="92" fill="none" stroke="var(--slate)" stroke-width=".7" opacity=".7"/>'
        for rx_ in (24, 52, 78)
    )
    lats = "".join(
        f'<ellipse cx="100" cy="{y}" rx="{w}" ry="{h}" fill="none" stroke="var(--slate)" stroke-width=".7" opacity=".55"/>'
        for y, w, h in ((100, 92, 12), (62, 78, 9), (138, 78, 9), (30, 44, 5), (170, 44, 5))
    )
    return (
        '<svg viewBox="0 0 200 200" width="100%" height="100%" aria-hidden="true">'
        '<defs><radialGradient id="gl" cx="32%" cy="26%" r="80%"><stop offset="0" stop-color="var(--navy)" stop-opacity=".82"/>'
        '<stop offset="1" stop-color="var(--navy)"/></radialGradient></defs>'
        '<circle cx="100" cy="100" r="94" fill="url(#gl)"/>'
        f'<g>{lines}{lats}</g>'
        '<path d="M58 118 Q84 40 138 62" fill="none" stroke="var(--accent)" stroke-width="2"/>'
        '<circle cx="58" cy="118" r="3.2" fill="var(--ivory)"/><circle cx="138" cy="62" r="4" fill="var(--accent)" stroke="var(--ivory)" stroke-width="1.5"/>'
        '</svg>'
    )


def _stamp_svg() -> str:
    return (
        '<svg viewBox="0 0 120 120" width="100%" aria-hidden="true">'
        '<defs><path id="arc" d="M60 60 m-44 0 a44 44 0 1 1 88 0 a44 44 0 1 1 -88 0"/></defs>'
        '<circle cx="60" cy="60" r="55" fill="none" stroke="var(--accent-deep)" stroke-width="2"/>'
        '<circle cx="60" cy="60" r="36" fill="none" stroke="var(--accent-deep)" stroke-width="1"/>'
        '<text font-family="IBM Plex Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="3.2" fill="var(--accent-deep)">'
        '<textPath href="#arc" startOffset="0">MERIDIAN · CLEARED FOR DEPARTURE · </textPath></text>'
        f'<svg x="36" y="34" width="48" height="52" viewBox="{B.MONO_VIEWBOX}" preserveAspectRatio="xMidYMid meet"><g transform="translate(0,{B.MONO_H}) scale(0.1,-0.1)" fill="var(--accent-deep)"><path d="{B.MONO_MAIN_PATH}"/><path d="{B.MONO_STAR_PATH}"/></g></svg>'
        '</svg>'
    )


def _kv(k: str, v: str):
    return rx.el.div(rx.el.span(k, class_name="mono"), rx.el.b(v), class_name="kv")


def scene():
    d = mock.SCENE
    return rx.el.div(
        rx.el.div(class_name="desk"),
        # globe (behind everything else)
        rx.el.div(
            rx.el.div(rx.html(_globe_fallback_svg()), class_name="globe-fallback"),
            rx.el.canvas(custom_attrs={"data-globe": "hero", "data-unis": unis_json(), "data-arcs": "first", "data-spin": "tilt"}),
            rx.el.div(class_name="globe-shadow"),
            class_name="layer globe-wrap globe3d", custom_attrs={"data-depth": "0.6", "data-rot": "0"}, id="globe-wrap",
        ),
        # passport
        rx.el.div(
            rx.el.div(monogram(78, ink="var(--ivory)", accent="var(--accent)"), class_name="emboss"),
            rx.el.span("STUDENT PASSPORT", class_name="mono on-navy", style={"fontSize": "9px", "textAlign": "center"}),
            rx.el.span("USA", class_name="mono on-navy", style={"fontSize": "9px"}),
            class_name="layer passport", custom_attrs={"data-depth": "0.9", "data-rot": "-9"},
        ),
        # boarding pass
        rx.el.div(
            rx.el.div(
                rx.el.div(class_name="strip"),
                rx.el.div(
                    rx.el.span("BOARDING PASS", class_name="mono blue", style={"fontSize": "9.5px"}),
                    rx.el.p("Aarav Mehta", class_name="serif", style={"margin": "6px 0 0", "fontSize": "20px", "fontWeight": 600}),
                    rx.el.div(
                        rx.el.div(rx.el.span("FROM", class_name="mono", style={"fontSize": "9px"}), rx.el.p("BOM", class_name="serif", style={"margin": 0, "fontSize": "24px", "fontWeight": 600})),
                        rx.el.span("→", style={"color": "var(--accent-deep)", "fontSize": "20px"}),
                        rx.el.div(rx.el.span("TO", class_name="mono", style={"fontSize": "9px"}), rx.el.p("USA", class_name="serif", style={"margin": 0, "fontSize": "24px", "fontWeight": 600})),
                        class_name="row", style={"gap": "14px", "marginTop": "8px"},
                    ),
                    rx.el.div(class_name="barcode"),
                    class_name="main",
                ),
                style={"flex": 1},
            ),
            rx.el.div(
                rx.el.span("INTAKE", class_name="mono", style={"fontSize": "9px"}),
                rx.el.p("FALL 27", class_name="serif", style={"margin": "2px 0 10px", "fontSize": "17px", "fontWeight": 600}),
                rx.el.span("GATE", class_name="mono", style={"fontSize": "9px"}),
                rx.el.p("M", class_name="serif", style={"margin": "2px 0 0", "fontSize": "17px", "fontWeight": 600}),
                class_name="stub",
            ),
            class_name="layer boarding", custom_attrs={"data-depth": "1.2", "data-rot": "-5"},
        ),
        # shortlist slip
        rx.el.div(
            rx.el.span("SHORTLIST", class_name="mono blue", style={"fontSize": "9px"}),
            rx.el.p("Carnegie Mellon", style={"margin": "6px 0 0"}, class_name=""),
            rx.el.p("UT Austin"), rx.el.p("Georgia Tech"),
            class_name="layer shortlist", custom_attrs={"data-depth": "1.5", "data-rot": "3"},
        ),
        # dossier (foreground)
        rx.el.div(
            rx.el.div(rx.el.span("STUDENT DOSSIER", class_name="mono ink", style={"fontSize": "9.5px"}), class_name="folder-tab"),
            rx.el.div(
                rx.el.div(
                    wordmark(24),
                    class_name="row", style={"gap": "10px", "marginBottom": "10px"},
                ),
                rx.el.p("Study Abroad Dossier", class_name="serif", style={"margin": "0 0 12px", "fontSize": "26px", "fontWeight": 600, "lineHeight": 1.1}),
                _kv("DATE", d["date"]), _kv("DESTINATION", d["destination"]), _kv("PROGRAM", d["program"]),
                _kv("APPLICATION NO.", d["application_no"]), _kv("STATUS", d["status"]),
                class_name="folder",
            ),
            class_name="layer dossier", custom_attrs={"data-depth": "2", "data-rot": "1.6"},
        ),
        rx.el.div(rx.html(_stamp_svg()), class_name="layer stamp-abs", style={"width": "17%"}, custom_attrs={"data-depth": "2.4", "data-rot": "-8"}),
        class_name="scene", id="meridian-scene",
    )
