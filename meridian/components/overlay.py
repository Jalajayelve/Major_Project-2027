"""Cinematic 'open the dossier' transition shown while State.opening is true."""
import reflex as rx

from ..state import State
from .brand import monogram, wordmark


def opening_overlay():
    return rx.cond(
        State.opening,
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.span("STUDENT DOSSIER", class_name="mono blue"),
                    rx.el.p("Profile", class_name="h2", style={"marginTop": "10px"}),
                    rx.el.hr(class_name="rule", style={"margin": "18px 0"}),
                    rx.el.div(class_name="rule", style={"height": "8px", "margin": "12px 0", "background": "var(--paper)"}),
                    rx.el.div(class_name="rule", style={"height": "8px", "margin": "12px 0", "background": "var(--paper)", "width": "70%"}),
                    class_name="open-page",
                ),
                rx.el.div(
                    monogram(96, ink="var(--ivory)"),
                    wordmark(30, on_navy=True),
                    rx.el.span("STUDENT DOSSIER", class_name="mono on-navy"),
                    class_name="open-cover",
                ),
                class_name="open-scene", style={"position": "relative"},
            ),
            class_name="opening",
        ),
        rx.fragment(),
    )
