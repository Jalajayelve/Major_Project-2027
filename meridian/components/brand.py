"""MERIDIAN brand: the client's wordmark + M monogram (traced from the mockup).

Reused as navbar logo, favicon, loading mark, report watermark, agent mark and
document stamp. Vector data lives in meridian/brand_assets.py (generated).
"""
import reflex as rx

from .. import brand_assets as B


def _vb(vb: str):
    x, y, w, h = (int(v) for v in vb.split())
    return x, y, w, h


def wordmark_svg(height: int = 30, ink: str = "var(--ink)", dot: str = "var(--accent)") -> str:
    x, y, w, h = _vb(B.WORDMARK_VIEWBOX)
    width = round(height * w / h)
    cx, cy, r = B.WORDMARK_DOT
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{B.WORDMARK_VIEWBOX}" width="{width}" height="{height}" role="img" aria-label="Meridian" style="display:block;max-width:100%;height:auto">'
        f'<g transform="translate(0,{B.WORDMARK_H}) scale(0.1,-0.1)" fill="{ink}"><path d="{B.WORDMARK_PATH}"/></g>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{dot}"/></svg>'
    )


def monogram_svg(size: int = 40, ink: str = "var(--ink)", accent: str = "var(--accent)", ring: bool = True) -> str:
    x, y, w, h = _vb(B.MONO_VIEWBOX)
    width = round(size * w / h)
    g = f'transform="translate(0,{B.MONO_H}) scale(0.1,-0.1)"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{B.MONO_VIEWBOX}" width="{width}" height="{size}" aria-hidden="true">'
        f'<g {g} fill="{ink}"><path d="{B.MONO_MAIN_PATH}"/></g>'
        f'<g {g} fill="{accent}"><path d="{B.MONO_STAR_PATH}"/></g></svg>'
    )


def wordmark(height: int = 30, on_navy: bool = False, max_width: str | None = None):
    ink = "var(--ivory)" if on_navy else "var(--ink)"
    style = {"display": "inline-flex", "lineHeight": 0}
    if max_width:
        style["maxWidth"] = max_width
    return rx.el.span(rx.html(wordmark_svg(height, ink)), style=style)


def monogram(size: int = 40, ink: str = "var(--ink)", accent: str = "var(--accent)", ring: bool = True):
    return rx.el.span(rx.html(monogram_svg(size, ink, accent)), style={"display": "inline-flex", "lineHeight": 0})


def brand(href: str = "/", on_navy: bool = False):
    return rx.el.a(wordmark(30, on_navy), href=href, class_name="brand", aria_label="Meridian home")


def watermark(size: int = 360, ink: str = "var(--ink)"):
    return rx.el.div(monogram(size, ink=ink, accent=ink), class_name="watermark wm")
