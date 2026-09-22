import reflex as rx

from ..components.brand import monogram, wordmark
from ..components.common import label, primary_button, section_head, start_button
from ..components.navbar import navbar
from ..components.globe3d import globe3d
from ..components.overlay import opening_overlay
from ..components.scene import scene
from ..data import mock


def hero():
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                label("Study abroad · MS / MBA · United States", "blue"),
                rx.el.h1(
                    rx.el.span("Meridian", class_name="sr-only"),
                    wordmark(112, max_width="100%"),
                    style={"marginTop": "26px", "fontSize": 0, "lineHeight": 0},
                ),
                rx.el.p("You bring the ambition.", rx.el.br(), "We map the journey.", class_name="tagline", style={"marginTop": "30px"}),
                rx.el.p(
                    "Seven specialist agents study your profile, your documents and the US programs that fit, "
                    "then hand you one personal dossier: where to apply, your odds, what it costs and how to fund it.",
                    class_name="lede", style={"marginTop": "26px"},
                ),
                rx.el.div(
                    start_button(),
                    rx.el.a("See how it works", href="/#how", class_name="nav-link", style={"color": "var(--accent-deep)"}),
                    class_name="row wrap", style={"gap": "30px", "marginTop": "40px"},
                ),
                class_name="page-enter",
            ),
            scene(),
            class_name="container hero-grid",
        ),
        style={"padding": "64px 0 96px"},
    )


def how_it_works():
    cards = [
        rx.el.div(
            label(s["no"], "blue"),
            rx.el.h3(s["title"], class_name="h3", style={"margin": "14px 0 10px"}),
            rx.el.p(s["text"], class_name="body"),
            class_name="sheet sheet-pad reveal" + (" stacked" if i == 3 else ""),
            style={"--d": f"{i * 0.12}s"}, custom_attrs={"data-tilt": "1"},
        )
        for i, s in enumerate(mock.STEPS)
    ]
    return rx.el.section(
        rx.el.div(
            rx.el.div(section_head("I", "How it works", "Four steps from ambition to a plan", "Each step is short. You can stop and come back."), class_name="reveal"),
            rx.el.div(*cards, class_name="grid-4"),
            class_name="container",
        ),
        id="how", class_name="section", style={"background": "var(--paper)", "borderTop": "1px solid var(--rule)", "borderBottom": "1px solid var(--rule)"},
    )


def journey_band():
    stops = [
        rx.el.div(
            rx.el.div(
                rx.el.span(a["no"], class_name="serif", style={"fontSize": "26px", "color": "var(--accent)", "fontWeight": 600}),
                rx.el.div(style={"flex": 1, "height": "0", "borderTop": "1.5px dashed var(--accent)", "opacity": ".6", "marginLeft": "12px"}),
                class_name="row",
            ),
            rx.el.h3(a["name"], class_name="h3", style={"margin": "12px 0 8px", "color": "var(--ivory)"}),
            rx.el.p(a["desc"], class_name="body", style={"color": "rgba(246,242,234,.72)", "fontSize": "14px"}),
            class_name="reveal", style={"--d": f"{i * 0.09}s"},
        )
        for i, a in enumerate(mock.AGENTS)
    ]
    return rx.el.section(
        globe3d("band", class_name="globe-band", spin="scroll", arcs="all", dark_surface=True),
        rx.el.div(
            rx.el.div(
                rx.el.div(rx.el.hr(class_name="rule-blue"), label("The journey", "on-navy"), class_name="row", style={"gap": "14px"}),
                rx.el.h2("Seven agents. One investigation.", class_name="h2", style={"marginTop": "14px", "color": "var(--ivory)"}),
                rx.el.p("Each agent takes one question about your future abroad and answers it before the next one begins.", class_name="body", style={"marginTop": "10px", "color": "rgba(246,242,234,.72)", "maxWidth": "58ch"}),
                style={"marginBottom": "44px"},
            ),
            rx.el.div(*stops, style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit,minmax(170px,1fr))", "gap": "36px 28px", "maxWidth": "800px"}),
            class_name="container", style={"position": "relative", "zIndex": 2},
        ),
        id="journey", class_name="section navy", style={"position": "relative", "overflow": "hidden"},
    )


def about():
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(section_head("II", "About", "Built for the student, not the algorithm"), class_name="reveal"),
                rx.el.p(
                    "Choosing where to study abroad is one of the largest decisions of your early life. "
                    "MERIDIAN turns scattered advice, spreadsheets and guesswork into a single, readable plan "
                    "you can take to your family, your referees and your bank.",
                    class_name="lede",
                ),
                style={"maxWidth": "620px"},
            ),
            rx.el.div(
                rx.el.div(rx.el.h3("Explained, not asserted", class_name="h3"), rx.el.p("Every probability comes with the factors that moved it, in plain language.", class_name="body", style={"marginTop": "8px"}), class_name="sheet sheet-pad reveal", custom_attrs={"data-tilt": "1"}),
                rx.el.div(rx.el.h3("Honest about cost", class_name="h3"), rx.el.p("Tuition, living costs and funding gaps are shown side by side with your budget.", class_name="body", style={"marginTop": "8px"}), class_name="sheet sheet-pad reveal", custom_attrs={"data-tilt": "1"}),
                rx.el.div(rx.el.h3("Yours to keep", class_name="h3"), rx.el.p("Download the finished report as a PDF and share it with the people who are helping you.", class_name="body", style={"marginTop": "8px"}), class_name="sheet sheet-pad reveal", custom_attrs={"data-tilt": "1"}),
                class_name="grid-3", style={"marginTop": "40px"},
            ),
            rx.el.div(
                rx.el.div(monogram(44), class_name="row"),
                rx.el.p("Ready when you are.", class_name="h2"),
                start_button(),
                class_name="row wrap between reveal", style={"gap": "24px", "marginTop": "64px", "paddingTop": "36px", "borderTop": "1px solid var(--rule-strong)"},
            ),
            class_name="container",
        ),
        id="about", class_name="section",
    )


def landing_page():
    return rx.el.div(navbar(), hero(), how_it_works(), journey_band(), about(), opening_overlay())
