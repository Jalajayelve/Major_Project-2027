import reflex as rx

from ..components import results_sections as R
from ..components.brand import watermark
from ..components.common import count_num, label, section_head
from ..components.globe3d import globe3d
from ..components.navbar import journey_nav
from ..data import mock
from ..state import State

SECTIONS = [
    ("profile-strength", "Profile"), ("university-matches", "Universities"), ("program-recommendations", "Programs"),
    ("experimental-model-scores", "Model scores"), ("financial-estimate", "Costs"), ("scholarships", "Scholarships"),
    ("career-alignment", "Career"), ("extracurricular-strength", "Extracurricular"), ("key-factors", "Key factors"),
]


def _sheet(no, eyebrow, title, body, sub=None, stacked=False):
    return rx.el.section(
        section_head(no, eyebrow, title, sub), body,
        class_name="sheet sheet-pad reveal" + (" stacked" if stacked else ""), id=eyebrow.lower().replace(" ", "-"),
    )


def _index():
    return rx.el.nav(
        *[rx.el.a(rx.el.span(name), rx.el.i(), href=f"#{sid}") for sid, name in SECTIONS],
        class_name="section-index no-print", aria_label="Sections",
    )


def _chip(title: str, value: str, pos: dict, depth: str):
    return rx.el.div(rx.el.span(title, class_name="mono", style={"fontSize": "9.5px"}), rx.el.b(value), class_name="chip", style=pos, custom_attrs={"data-pd": depth})


def _cover():
    return rx.el.div(
        watermark(420, ink="var(--ivory)"),
        rx.el.div(
            rx.el.div(
                label("Your personal dossier", "on-navy"),
                rx.el.h1(State.student_name, class_name="h1", style={"color": "var(--ivory)", "marginTop": "14px"}),
                rx.el.div(
                    rx.el.div(label("Target", "on-navy"), rx.el.p("United States", style={"margin": "6px 0 0", "fontWeight": 500})),
                    rx.el.div(label("Program", "on-navy"), rx.el.p(State.target_program, style={"margin": "6px 0 0", "fontWeight": 500})),
                    rx.el.div(label("Intake", "on-navy"), rx.el.p(State.profile["intake"], style={"margin": "6px 0 0", "fontWeight": 500})),
                    class_name="row wrap", style={"gap": "44px", "marginTop": "30px"},
                ),
                rx.el.div(
                    label("Profile strength", "on-navy"),
                    rx.el.div(
                        rx.cond(State.agent7_ready,
                            rx.el.span(State.agent7_score, class_name="num-key", style={"fontSize": "84px"}, key=State.agent7_score,
                                       custom_attrs={"data-count": State.agent7_count, "data-suffix": State.agent7_count_suffix}),
                            rx.el.span("Not scored", class_name="num-key", style={"fontSize": "84px"})),
                        rx.el.span(rx.cond(State.agent7_ready, "out of 100 · " + State.agent7_tier, "Complete your Agent 7 inputs"), class_name="mono on-navy"),
                        class_name="row", style={"gap": "16px", "alignItems": "baseline", "marginTop": "6px"},
                    ),
                    style={"marginTop": "34px"},
                ),
                rx.el.div(
                    rx.el.button("Download report", class_name="btn-download", type="button", on_click=State.download_report),
                    rx.el.a(rx.el.button("View printable report", class_name="btn-ghost", type="button", style={"color": "var(--ivory)", "borderColor": "var(--rule-on-navy)"}), href="/report"),
                    class_name="row wrap", style={"gap": "16px", "marginTop": "34px"},
                ),
            ),
            rx.el.div(
                globe3d("dash", class_name="globe-dash", spin="auto", arcs="all", drag=True, dark_surface=True, destinations=[],
                        custom_attrs={"data-sp": "0.16"}),
                _chip("Universities matched", State.university_count, {"left": "-2%", "top": "8%"}, "1.5"),
                _chip("Schools with scores", State.university_scored_count, {"right": "-1%", "top": "44%"}, "2.4"),
                _chip("Demo cost / yr", mock.FINANCIAL["total_str"], {"left": "4%", "bottom": "9%"}, "1.9"),
                rx.el.p("Move your cursor · drag to rotate", class_name="mono on-navy", style={"textAlign": "center", "marginTop": "10px", "fontSize": "10px"}),
                class_name="globe-col", custom_attrs={"data-pgroup": "1"},
            ),
            class_name="cover-grid",
        ),
        class_name="cover page-enter",
    )


def results_page():
    return rx.el.div(
        journey_nav(3),
        _index(),
        globe3d("mini", class_name="globe-mini", spin="auto", arcs="all", destinations=[]),
        # read by the 3D globe so it can turn to the selected university
        rx.el.div(State.selected_uni, id="sel-uni", style={"display": "none"}),
        rx.el.main(
            rx.el.div(
                rx.el.p(State.analysis_scope, class_name="body", style={"marginBottom": "18px"}),
                _cover(),
                rx.el.div(
                    _sheet("01", "Profile strength", "Where you stand today", R.profile_strength()),
                    _sheet("02", "University matches", "Universities that fit you",
                           R.university_matches(),
                           "Agent 2 university matching status and results.", stacked=True),
                    _sheet("03", "Program recommendations", "Program suggestions ? Demonstration", R.programs_table()),
                    _sheet("04", "Experimental model scores", "Unvalidated scores, program by program", R.admission_probability(),
                           "These scores do not estimate your admission chances."),
                    _sheet("05", "Financial estimate", "Cost breakdown ? Demonstration", R.financial()),
                    _sheet("06", "Scholarships", "Funding examples ? Demonstration", R.scholarships()),
                    _sheet("07", "Career alignment", "Career examples ? Demonstration", R.career()),
                    _sheet("08", "Extracurricular strength", "Beyond grades and scores", R.extracurricular()),
                    _sheet("09", "Key factors", "Why the model said what it said", R.key_factors()),
                    rx.el.div(
                        rx.el.div(rx.el.h2("Take your dossier with you", class_name="h2"), rx.el.p("A finished PDF with every section above.", class_name="body", style={"marginTop": "8px"})),
                        rx.el.button("Download report", class_name="btn-download", type="button", on_click=State.download_report),
                        class_name="sheet sheet-pad row wrap between reveal", style={"gap": "24px", "background": "var(--accent-soft)", "borderTop": "4px solid var(--accent)"},
                    ),
                    style={"display": "flex", "flexDirection": "column", "gap": "32px", "marginTop": "40px"},
                ),
                class_name="container", style={"padding": "48px 28px 110px"},
            ),
        ),
    )
