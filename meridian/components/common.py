"""Small reusable building blocks."""
import reflex as rx

from ..state import State


def label(text, tone: str = "", **kw):
    return rx.el.span(text, class_name=f"mono {tone}".strip(), **kw)


def section_head(no: str, eyebrow: str, title: str, sub: str | None = None):
    return rx.el.div(
        rx.el.div(rx.el.hr(class_name="rule-blue"), label(f"{no}  {eyebrow}", "blue"), class_name="row", style={"gap": "14px"}),
        rx.el.h2(title, class_name="h2", style={"marginTop": "14px"}),
        *([rx.el.p(sub, class_name="body", style={"marginTop": "10px", "maxWidth": "60ch"})] if sub else []),
        style={"marginBottom": "28px"},
    )


def bar(width, key: bool = False, neg: bool = False):
    cls = "bar key" if key else ("bar neg" if neg else "bar")
    return rx.el.div(rx.el.i(style={"width": width}), class_name=cls)


def start_button(size: str = "", variant: str = ""):
    return rx.el.button(
        rx.el.span("Start Journey"),
        rx.el.span("→", class_name="tab-arrow"),
        on_click=State.start_journey,
        type="button",
        class_name=f"tab-button {size} {variant}".strip(),
    )


def primary_button(text: str, on_click, variant: str = "", disabled=False):
    return rx.el.button(
        rx.el.span(text), rx.el.span("→", class_name="tab-arrow"),
        on_click=on_click, type="button", disabled=disabled,
        class_name=f"tab-button {variant}".strip(),
    )


def count_num(value, prefix: str = "", suffix: str = "", tag: str = "p", cls: str = "num-key", style: dict | None = None):
    """A key number that counts up when scrolled into view (see assets/scene.js)."""
    el = rx.el.p if tag == "p" else rx.el.span
    return el(
        f"{prefix}{value:,}{suffix}", class_name=cls, style=style or {},
        custom_attrs={"data-count": str(value), "data-prefix": prefix, "data-suffix": suffix},
    )


def kv(k: str, v):
    return rx.el.div(label(k), rx.el.span(v, style={"fontWeight": 500}), class_name="kv-row")
