import reflex as rx

from ..components import results_sections as R
from ..components.brand import watermark
from ..components.common import count_num, label, section_head
from ..components.globe3d import globe3d
from ..components.map import uni_chips, uni_info_cards, university_map
from ..components.navbar import journey_nav
from ..data import mock
from ..state import State

SECTIONS = [
    ("profile-strength", "Profile"), ("university-matches", "Universities"), ("program-recommendations", "Programs"),
    ("admission-probability", "Admission"), ("financial-estimate", "Costs"), ("scholarships", "Scholarships"),
    ("career-alignment", "Career"), ("extracurricular-strength", "Extracurricular"), ("key-factors", "Key factors"),
]


def _sheet(no, eyebrow, title, body, sub=None, stacked=False):
    return rx.el.section(
        section_head(no, eyebrow, title, sub), body,
        class_name="sheet sheet-pad" + (" stacked" if stacked else ""), id=eyebrow.lower().replace(" ", "-"),
    )


def _index():
    return rx.el.nav(
        *[rx.el.a(rx.el.span(name), rx.el.i(), href=f"#{sid}") for sid, name in SECTIONS],
        class_name="section-index no-print", aria_label="Sections",
    )


def _chip(title: str, value: str, pos: dict, depth: str):
    return rx.el.div(rx.el.span(title, class_name="mono", style={"fontSize": "9.5px"}), rx.el.b(value), class_name="chip", style=pos, custom_attrs={"data-pd": depth})


def _cover():
    ps = mock.PROFILE_STRENGTH
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
                        count_num(ps["score"], tag="span", style={"fontSize": "84px"}),
                        rx.el.span("out of 100 · " + ps["label"], class_name="mono on-navy"),
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
                globe3d("dash", class_name="globe-dash", spin="auto", arcs="all", select=True, drag=True, dark_surface=True,
                        custom_attrs={"data-sp": "0.16"}),
                _chip("Universities matched", str(len(mock.UNIVERSITIES)), {"left": "-2%", "top": "8%"}, "1.5"),
                _chip("Target schools", str(sum(1 for u in mock.UNIVERSITIES if u["tier"] == "Target")), {"right": "-1%", "top": "44%"}, "2.4"),
                _chip("Estimated cost / yr", mock.FINANCIAL["total_str"], {"left": "4%", "bottom": "9%"}, "1.9"),
                rx.el.p("Move your cursor · drag to rotate", class_name="mono on-navy", style={"textAlign": "center", "marginTop": "10px", "fontSize": "10px"}),
                class_name="globe-col", custom_attrs={"data-pgroup": "1"},
            ),
            class_name="cover-grid",
        ),
        class_name="cover page-enter",
    )


def original_demo_layout():
    return rx.el.div(
        journey_nav(3),
        _index(),
        globe3d("mini", class_name="globe-mini", spin="auto", arcs="all"),
        # read by the 3D globe so it can turn to the selected university
        rx.el.div(State.selected_uni, id="sel-uni", style={"display": "none"}),
        rx.el.main(
            rx.el.div(
                _cover(),
                rx.el.div(
                    _sheet("01", "Profile strength", "Where you stand today", R.profile_strength()),
                    _sheet("02", "University matches", "Universities that fit you",
                           rx.el.div(rx.el.div(rx.el.div(university_map(), uni_chips()), uni_info_cards(), class_name="split")),
                           "Select a university to see its details. The globe at the top of the page will turn to face it.", stacked=True),
                    _sheet("03", "Program recommendations", "Programs worth applying to", R.programs_table()),
                    _sheet("04", "Admission probability", "Your odds, school by school", R.admission_probability(),
                           "Illustrative estimates from your profile. They are not guarantees."),
                    _sheet("05", "Financial estimate", "What it will cost", R.financial()),
                    _sheet("06", "Scholarships", "Funding you may qualify for", R.scholarships()),
                    _sheet("07", "Career alignment", "Where this degree can lead", R.career()),
                    _sheet(
                        "08",
                        "Extracurricular strength",
                        "Beyond grades and scores",
                        rx.cond(State.agent7_available, R.live_extracurricular(), R.extracurricular()),
                    ),
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


def results_page():
    def card(row):
        return rx.el.article(label(row["country"], "blue"), rx.el.h3(row["name"], class_name="h3"), rx.el.p("Catalog tier: ", row["tier"], class_name="body"), rx.el.p("Catalog GPA: ", row["gpa"], class_name="mono"), class_name="sheet sheet-pad stacked")
    def program_card(row):
        return rx.el.article(
            rx.el.h3(row["program_name"], class_name="h3"),
            rx.el.p(row["university"], class_name="body"),
            rx.el.p(
                "Fit score: ", row["specialization_fit_score"],
                " · Match score: ", row["match_score"],
                " · ", row["duration"], " · ", row["mode"],
                class_name="mono", style={"marginTop": "8px"},
            ),
            class_name="sheet sheet-pad stacked",
        )
    return rx.el.div(journey_nav(3), rx.el.main(
        rx.el.section(label("Your personal dossier", "on-navy"), rx.el.h1(State.student_name, class_name="h1", style={"color":"var(--ivory)"}), rx.el.p(State.target_program, class_name="lede"),
            rx.el.div(rx.el.button("Download report", on_click=State.download_report, class_name="btn-download"), rx.el.a("Printable report", href="/report", class_name="btn-ghost"), class_name="row wrap no-print", style={"gap":"20px","marginTop":"24px"}), class_name="navy sheet-pad stacked"),
        _sheet("01", "Profile", "Your profile analysis", rx.cond(
            State.prediction_unavailable,
            rx.el.p(
                "Profile prediction unavailable. The MS/MBA prediction model is not installed, so no prediction is shown.",
                class_name="notice",
            ),
            rx.el.p(State.prediction_text, class_name="lede"),
        )),
        _sheet("02", "University matches", "Possibilities to explore", rx.el.div(
            rx.el.p("These are university results returned by the backend matcher.", class_name="notice"),
            rx.cond(State.recommendations.length()>0, rx.el.div(rx.foreach(State.recommendations, card), class_name="result-list"), rx.el.p("No matches saved. Complete your academic details and matching preferences, then run analysis. An empty shortlist may also mean no catalog entries met your filters.", class_name="lede")))),
        _sheet("03", "Program rankings", "Programs ranked for your shortlist", rx.cond(
            State.program_results.length() > 0,
            rx.el.div(
                rx.el.p("Agent 3 program-fit rankings use the Agent 2 university shortlist. Scores are relevance rankings, not admission probabilities.", class_name="notice"),
                rx.el.div(rx.foreach(State.program_results, program_card), class_name="result-list"),
            ),
            rx.el.p("No Agent 3 program rankings were saved.", class_name="lede"),
        )),
        _sheet(
            "04",
            "Extracurricular strength",
            "Beyond grades and scores",
            rx.cond(State.agent7_available, R.live_extracurricular(), rx.el.p(State.agent7_summary, class_name="notice")),
        ),
        rx.el.section(label("Additional chapters"), rx.el.h2("Still to come", class_name="h2"), rx.el.p("Financial, scholarship and career analysis are unavailable through the current API. No scores or estimates have been generated for those sections.", class_name="body"), class_name="sheet sheet-pad"),
        rx.el.details(rx.el.summary("Inspect the actual API response"), rx.el.pre(State.result_json, style={"whiteSpace":"pre-wrap","overflowWrap":"anywhere"}), class_name="sheet sheet-pad"),
        class_name="container", style={"padding":"48px 28px 96px","display":"grid","gap":"28px"}))
