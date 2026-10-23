import reflex as rx

from ..components.brand import brand, monogram
from ..components.common import label
from ..components.globe3d import globe3d
from ..data import mock
from ..state import State
from .account import notice


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
    unavailable_note = rx.cond(
        status == "unavailable",
        rx.el.p(
            "No verified backend service is configured for this agent in the current environment.",
            class_name="body",
            style={"fontSize": "13px", "marginTop": "4px"},
        ),
        rx.fragment(),
    )
    cls = rx.cond(
        status == "processing",
        "agent-card processing",
        rx.cond(status == "completed", "agent-card completed", rx.cond(status == "failed", "agent-card failed", "agent-card waiting")),
    )
    node_cls = rx.cond(
        status == "completed",
        "node completed",
        rx.cond(status == "processing", "node processing", rx.cond(status == "failed", "node failed", rx.cond(status == "unavailable", "node unavailable", "node"))),
    )
    right = rx.cond(
        status == "completed",
        rx.el.span("Completed", class_name="stamp"),
        rx.cond(
            status == "processing",
            rx.el.div(
                rx.el.span("Request running…", class_name="mono blue request-busy", style={"fontWeight": 600}),

            ),
            rx.cond(
                status == "failed",
                rx.el.span("Failed", class_name="status-failed"),
                rx.cond(
                    status == "unavailable",
                    rx.el.span("Unavailable", class_name="status-unavailable"),
                    rx.el.span("Waiting", class_name="mono on-navy"),
                ),
            ),
        ),
    )
    return rx.el.div(
        rx.el.div(rx.cond(status == "completed", "✓", ""), class_name=node_cls),
        rx.el.div(
            rx.el.span(a["no"], class_name="agent-no"),
            rx.el.div(
                rx.el.h3(a["name"], " agent", class_name="h3"),
                rx.el.p(a["desc"], class_name="body", style={"fontSize": "14px", "marginTop": "4px"}),
                unavailable_note,
                style={"minWidth": 0},
            ),
            rx.el.div(right, class_name="agent-status"),
            class_name=cls,
        ),
        class_name="agent-row",
    )


def analysis_page():
    def university_card(row):
        return rx.el.article(
            rx.el.div(
                rx.el.span(row["country"], class_name="mono blue"),
                rx.el.span("Catalog match", class_name="mono"),
                class_name="row between wrap", style={"gap": "12px"},
            ),
            rx.el.h3(row["name"], class_name="h3", style={"marginTop": "12px"}),
            rx.el.p("Catalog tier: ", row["tier"], class_name="body", style={"marginTop": "8px"}),
            rx.el.p("Catalog GPA: ", row["gpa"], class_name="mono", style={"marginTop": "6px"}),
            class_name="sheet sheet-pad stacked",
        )

    return rx.el.div(
        notice(),
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
                        label("Live backend requests", "on-navy"),
                        rx.el.h1("Your dossier, under review", class_name="h1", style={"marginTop": "12px", "color": "var(--ivory)", "maxWidth": "18ch"}),
                        rx.el.div(
                            rx.el.span(State.overall_pct, class_name="num-key", style={"fontSize": "44px"}),
                            rx.el.span(State.agents_completed_count.to_string() + " of 2 API requests completed", class_name="mono on-navy"),
                            class_name="row", style={"gap": "16px", "marginTop": "28px", "alignItems": "baseline"},
                        ),
                        rx.el.p("Five agents are not exposed through an operational API. No simulated progress is shown.", class_name="body on-navy"),
                        rx.cond(
                            State.analysis_error != "",
                            rx.el.p(State.analysis_error, class_name="notice", role="alert", style={"marginTop": "20px"}),
                            rx.fragment(),
                        ),
                        rx.cond(
                            (~State.matching_ready) & (State.recommendations.length() == 0),
                            rx.el.p(
                                "University matching needs a country and catalog tier. "
                                "Open Study Goals to choose both, save your profile, then retry analysis.",
                                class_name="notice", role="status", style={"marginTop": "12px"},
                            ),
                            rx.fragment(),
                        ),
                        style={"marginBottom": "56px"}, class_name="page-enter",
                    ),
                    rx.el.div(rx.el.button("Run / retry analysis", on_click=State.run_agents, disabled=State.agents_running, class_name="tab-button on-navy"), rx.el.a("Dashboard", href="/dashboard", class_name="btn-ghost"), style={"marginBottom":"24px"}),
                    rx.cond(
                        State.prediction_unavailable,
                        rx.el.div(
                            rx.el.h2("Profile prediction unavailable", class_name="h2"),
                            rx.el.p(
                                "The matching results below are still valid. No profile prediction is shown; the backend error above explains whether input data or the unavailable MS/MBA model caused the failure.",
                                class_name="body", style={"marginTop": "10px"},
                            ),
                            class_name="notice", role="status", style={"maxWidth": "860px", "marginTop": "32px"},
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.recommendations.length() > 0,
                        rx.el.section(
                            rx.el.div(
                                rx.el.h2("University matching results", class_name="h2"),
                                rx.el.p(
                                    "These are the universities returned by the backend catalog matcher.",
                                    class_name="body", style={"marginTop": "8px"},
                                ),
                                class_name="page-enter",
                            ),
                            rx.el.div(rx.foreach(State.recommendations, university_card), class_name="grid-2", style={"marginTop": "20px"}),
                            style={"maxWidth": "860px", "marginTop": "44px"},
                        ),
                        rx.fragment(),
                    ),
                    rx.el.div(rx.foreach(State.agents, _agent), class_name="route", style={"maxWidth": "860px", "marginTop": "36px"}),
                    rx.el.div(
                        rx.el.div(
                            rx.foreach(State.event_log, lambda e: rx.el.span(e, class_name="mono on-navy", style={"display": "block", "fontSize": "10.5px"})),
                            style={"minHeight": "64px"},
                        ),
                        rx.cond(
                            State.agents_done,
                            rx.el.button(
                                rx.el.span("View available results"), rx.el.span("→", class_name="tab-arrow"),
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
