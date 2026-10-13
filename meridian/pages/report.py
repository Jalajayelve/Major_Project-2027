import reflex as rx

from ..components import results_sections as R
from ..components.brand import monogram, watermark, wordmark
from ..components.common import label
from ..components.navbar import journey_nav
from ..data import mock
from ..state import State


def _page(no: str, title: str, body, eyebrow: str):
    return rx.el.section(
        watermark(300),
        rx.el.div(
            rx.el.div(rx.el.hr(class_name="rule-blue"), label(f"Section {no}  {eyebrow}", "blue"), class_name="row", style={"gap": "14px"}),
            rx.el.h2(title, class_name="h2", style={"margin": "12px 0 28px"}),
            body, style={"position": "relative", "zIndex": 2},
        ),
        class_name="report-page",
    )


def report_page():
    cover = rx.el.section(
        watermark(420),
        rx.el.div(
            rx.el.div(wordmark(44), class_name="row"),
            rx.el.div(label("Study abroad report", "blue"), style={"margin": "90px 0 14px"}),
            rx.el.h1(State.student_name, class_name="h1", style={"fontSize": "clamp(38px,6vw,64px)"}),
            rx.el.div(
                rx.el.div(label("Target"), rx.el.p("United States", style={"margin": "6px 0 0", "fontWeight": 500})),
                rx.el.div(label("Program"), rx.el.p(State.target_program, style={"margin": "6px 0 0", "fontWeight": 500})),
                rx.el.div(label("Intake"), rx.el.p(State.profile["intake"], style={"margin": "6px 0 0", "fontWeight": 500})),
                class_name="row wrap", style={"gap": "44px", "marginTop": "32px"},
            ),
            rx.el.hr(class_name="rule", style={"margin": "48px 0 28px"}),
            rx.el.div(label("Profile strength"), rx.el.p(State.agent7_score, class_name="num-key", style={"fontSize": "84px", "marginTop": "8px"})),
            rx.el.div(
                label("Top recommendations"),
                R.university_matches(),
                style={"marginTop": "28px"},
            ),
            rx.el.div(rx.el.span("Prepared", class_name="mono"), rx.el.span(f"Report no. {mock.build_report()['student']['report_no']}", class_name="mono"), class_name="row between", style={"marginTop": "60px"}),
            style={"position": "relative", "zIndex": 2},
        ),
        class_name="report-page", style={"minHeight": "880px"},
    )
    return rx.el.div(
        journey_nav(4),
        rx.el.main(
            rx.el.div(
                rx.el.div(
                    rx.el.div(label("Step 4 of 4", "blue"), rx.el.h1("Your report", class_name="h1", style={"marginTop": "8px"})),
                    rx.el.div(
                        rx.el.button("Print", on_click=rx.call_script("window.print()"), type="button", class_name="btn-ghost"),
                        rx.el.button("Download report", on_click=State.download_report, type="button", class_name="btn-download"),
                        class_name="row wrap", style={"gap": "14px"},
                    ),
                    class_name="row wrap between no-print", style={"gap": "20px", "maxWidth": "820px", "margin": "0 auto 36px"},
                ),
                rx.el.p(State.analysis_scope, class_name="body", style={"maxWidth": "820px", "margin": "0 auto 20px"}),
                cover,
                _page("01", "University recommendations", R.admission_probability(), "Recommendations"),
                _page("02", "Program matches ? Demonstration", R.programs_table(), "Programs"),
                _page("03", "Cost breakdown ? Demonstration", R.financial(), "Financial"),
                _page("04", "Scholarships ? Demonstration", R.scholarships(), "Funding"),
                _page("05", "Career alignment ? Demonstration", R.career(), "Career"),
                _page("06", "Profile strength", R.profile_strength(), "Profile"),
                _page("07", "Extracurricular strength", R.extracurricular(), "Beyond grades"),
                _page("08", "Key model factors", R.key_factors(), "Explainability"),
                class_name="container", style={"padding": "48px 28px 110px"},
            ),
            style={"background": "var(--paper)"},
        ),
    )
