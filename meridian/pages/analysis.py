import reflex as rx

from ..components.brand import brand, monogram
from ..components.common import label
from ..components.globe3d import globe3d
from ..data import mock
from ..state import State


def _globe_bg() -> str:
    arcs = "".join(
        f'<ellipse cx="200" cy="200" rx="{r}" ry="190" fill="none" stroke="var(--ivory)" stroke-width=".6" opacity=".35"/>'
        for r in (40, 85, 130, 170)
    )
    lats = "".join(
        f'<ellipse cx="200" cy="{y}" rx="{w}" ry="{h}" fill="none" stroke="var(--ivory)" stroke-width=".6" opacity=".3"/>'
        for y, w, h in ((200, 190, 22), (130, 165, 18), (270, 165, 18), (70, 110, 11), (330, 110, 11))
    )
    return f'<svg viewBox="0 0 400 400" width="100%" aria-hidden="true"><circle cx="200" cy="200" r="192" fill="none" stroke="var(--ivory)" stroke-width=".9" opacity=".5"/>{arcs}{lats}<path d="M60 260 Q170 60 330 150" fill="none" stroke="var(--accent)" stroke-width="1.6" stroke-dasharray="4 6" opacity=".8"/></svg>'


def _agent(a):
    status = a["status"]
    cls = rx.cond(status == "processing", "agent-card processing", rx.cond(status == "completed", "agent-card completed", "agent-card waiting"))
    node_cls = rx.cond(status == "waiting", "node", rx.cond(status == "processing", "node processing", "node completed"))
    right = rx.cond(
        status == "completed",
        rx.el.span("Completed", class_name="stamp"),
        rx.cond(
            status == "processing",
            rx.el.div(
                rx.el.span("Processing ", a["pct"], class_name="mono blue", style={"fontWeight": 600}),
                rx.el.div(rx.el.i(style={"width": a["pct"]}), class_name="progress", style={"marginTop": "10px"}),
            ),
            rx.el.span("Waiting", class_name="mono"),
        ),
    )
    return rx.el.div(
        rx.el.div(rx.cond(status == "completed", "✓", ""), class_name=node_cls),
        rx.el.div(
            rx.el.span(a["no"], class_name="agent-no"),
            rx.el.div(
                rx.el.h3(a["name"], " agent", class_name="h3"),
                rx.el.p(a["desc"], class_name="body", style={"fontSize": "14px", "marginTop": "4px"}),
                style={"minWidth": 0},
            ),
            rx.el.div(right, class_name="agent-status"),
            class_name=cls,
        ),
        class_name="agent-row",
    )


def analysis_page():
    return rx.el.div(
        rx.el.div(
            globe3d("agents", class_name="globe-agents", spin="auto", arcs="progress", dark_surface=True),
            rx.el.div(State.agents_completed_count.to_string(), id="agent-progress", style={"display": "none"}),
            rx.el.header(
                rx.el.div(
                    brand(on_navy=True),
                    rx.el.div(
                        rx.el.span("Step 3 of 4", class_name="mono on-navy"),
                        class_name="row",
                    ),
                    class_name="container nav-inner",
                ),
                style={"borderBottom": "1px solid var(--rule-on-navy)", "position": "relative", "zIndex": 2},
            ),
            rx.el.main(
                rx.el.div(
                    rx.el.div(
                        label("Analysis in progress", "on-navy"),
                        rx.el.h1("Seven agents are studying your file", class_name="h1", style={"marginTop": "12px", "color": "var(--ivory)", "maxWidth": "18ch"}),
                        rx.el.div(
                            rx.el.span(State.overall_pct, class_name="num-key", style={"fontSize": "44px"}),
                            rx.el.span(State.agents_completed_count.to_string() + " of 7 complete", class_name="mono on-navy"),
                            class_name="row", style={"gap": "16px", "marginTop": "28px", "alignItems": "baseline"},
                        ),
                        rx.el.div(rx.el.i(style={"width": State.overall_pct}), class_name="progress", style={"marginTop": "14px", "maxWidth": "420px", "background": "var(--rule-on-navy)"}),
                        style={"marginBottom": "56px"}, class_name="page-enter",
                    ),
                    rx.el.div(rx.foreach(State.agents, _agent), class_name="route", style={"maxWidth": "860px"}),
                    rx.el.div(
                        rx.el.div(
                            rx.foreach(State.event_log, lambda e: rx.el.span(e, class_name="mono on-navy", style={"display": "block", "fontSize": "10.5px"})),
                            style={"minHeight": "64px"},
                        ),
                        rx.cond(
                            State.agents_done,
                            rx.el.button(
                                rx.el.span("Open your dossier"), rx.el.span("→", class_name="tab-arrow"),
                                on_click=rx.redirect("/results"), type="button", class_name="tab-button on-navy",
                            ),
                            rx.fragment(),
                        ),
                        class_name="row wrap between", style={"gap": "24px", "marginTop": "40px", "maxWidth": "860px", "alignItems": "flex-end"},
                    ),
                    class_name="container", style={"padding": "72px 28px 110px", "position": "relative", "zIndex": 2},
                ),
            ),
            class_name="navy", style={"minHeight": "100vh", "position": "relative", "overflow": "hidden"},
        ),
    )
