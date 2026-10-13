"""Editorial sections shared by the Results dashboard and the Report page."""
import reflex as rx

from ..data import mock
from ..state import State
from ..services.agent7 import NOTICE
from ..services.agent2 import NOTICE as AGENT2_NOTICE
from .common import bar, count_num, label


def profile_strength():
    return rx.cond(
        State.agent7_ready,
        rx.el.div(
            rx.el.div(
                label("Profile Strength · Agent 7"),
                rx.el.p(State.agent7_score, class_name="num-key", style={"fontSize": "96px", "margin": "6px 0 0"},
                          key=State.agent7_score, custom_attrs={"data-count": State.agent7_count, "data-suffix": State.agent7_count_suffix}),
                rx.el.span("out of 100", class_name="mono ink"),
            ),
            rx.el.div(
                *[rx.el.div(label(name), rx.el.span(value, class_name="mono ink"), class_name="kv-row")
                  for name, value in [("Strength Tier", State.agent7_tier), ("Achievement Archetype", State.agent7_archetype),
                                      ("Research Evidence", State.agent7_research), ("P(Strong)", State.agent7_probability)]],
                rx.el.p(NOTICE, class_name="body", style={"marginTop": "18px", "fontSize": "13px"}),
                rx.el.p("Archetypes are cluster IDs, not ranked labels. Research Evidence uses the reported publication/patent counts; it does not verify documents.", class_name="body", style={"marginTop": "10px", "fontSize": "13px"}),
            ),
            class_name="split", style={"gridTemplateColumns": "minmax(0,1fr) minmax(0,1.6fr)", "gap": "48px"},
            custom_attrs={"data-testid": "agent7-result"},
        ),
        rx.el.div(
            rx.el.p("Agent 7 has not scored this profile. Complete the eight Agent 7 fields in Experience and submit your profile.", class_name="body"),
            rx.el.a("Return to profile", href="/profile", class_name="nav-link"),
        ),
    )


def admission_probability():
    return university_matches()


def university_matches():
    head = rx.el.tr(*[rx.el.th(h) for h in ("University / program", "Experimental band", "Unvalidated model score", "Match score", "Catalog tuition")])
    return rx.cond(
        State.agent2_ready,
        rx.el.div(
            rx.el.p(AGENT2_NOTICE, class_name="body", style={"marginBottom": "20px"}),
            rx.cond(State.university_matches.length() == 0,
                    rx.el.p("No programs in the catalog matched your degree and field.", class_name="body"),
                    rx.el.div(rx.el.table(rx.el.thead(head), rx.el.tbody(rx.foreach(State.university_matches, lambda u:
                        rx.el.tr(rx.el.td(rx.el.b(u["name"]), rx.el.p(u["program"], class_name="body"), rx.el.p(u["note"], class_name="body")),
                                 rx.el.td(u["tier"]), rx.el.td(u["prob_str"]), rx.el.td(u["match_str"]), rx.el.td(u["tuition_str"]))
                    )), class_name="plain"), style={"overflowX": "auto"})),
            custom_attrs={"data-testid": "agent2-result"},
        ),
        rx.el.div(rx.el.p(State.agent2_status, class_name="body", role="status"),
                  rx.el.p("Run analysis to generate current experimental matches and scores.", class_name="body"),
                  custom_attrs={"data-testid": "agent2-unavailable"}),
    )


def programs_table():
    head = rx.el.tr(*[rx.el.th(h) for h in ("University", "Program", "Match", "Duration", "Focus")])
    body = [rx.el.tr(
        rx.el.td(p["university"], style={"fontWeight": 500}), rx.el.td(p["program"]),
        rx.el.td(p["match"], class_name="num-key", style={"fontSize": "20px"}), rx.el.td(p["duration"]), rx.el.td(p["focus"]),
    ) for p in mock.PROGRAMS]
    return rx.el.div(rx.el.table(rx.el.thead(head), rx.el.tbody(*body), class_name="plain"), style={"overflowX": "auto"})


def financial():
    f = mock.FINANCIAL
    palette = ["var(--accent)", "var(--ink)", "var(--navy)", "var(--slate)", "var(--paper-deep)"]
    return rx.el.div(
        rx.el.div(
            rx.el.div(label("Estimated total"), count_num(f["total"], prefix="$", style={"fontSize": "64px", "margin": "6px 0 0"}), rx.el.span(f["period"], class_name="mono")),
            rx.el.div(label("Your budget"), rx.el.p(f["budget_str"], class_name="serif", style={"fontSize": "34px", "fontWeight": 600, "margin": "6px 0 0"}), rx.el.span(f["gap_str"], class_name="mono ink")),
            class_name="row between wrap", style={"gap": "24px", "marginBottom": "28px"},
        ),
        rx.el.div(*[rx.el.div(style={"width": i["w"], "background": palette[n]}, title=i["name"]) for n, i in enumerate(f["items"])], class_name="stacked-bar"),
        rx.el.div(
            *[rx.el.div(
                rx.el.span(rx.el.span(style={"display": "inline-block", "width": "10px", "height": "10px", "background": palette[n], "marginRight": "10px"}), i["name"]),
                rx.el.span(i["amount"], style={"fontWeight": 600}), class_name="kv-row",
            ) for n, i in enumerate(f["items"])],
            style={"marginTop": "22px"},
        ),
    )


def scholarships():
    head = rx.el.tr(*[rx.el.th(h) for h in ("Award", "Type", "Value", "Fit")])
    body = [rx.el.tr(
        rx.el.td(s["name"], style={"fontWeight": 500}), rx.el.td(s["type"]), rx.el.td(s["value"]),
        rx.el.td(rx.el.span(s["fit"], class_name="tier blue" if s["fit"] == "High" else "tier")),
    ) for s in mock.SCHOLARSHIPS]
    return rx.el.div(rx.el.table(rx.el.thead(head), rx.el.tbody(*body), class_name="plain"), style={"overflowX": "auto"})


def career():
    c = mock.CAREER
    return rx.el.div(
        rx.el.p(c["summary"], class_name="lede", style={"marginBottom": "28px"}),
        *[rx.el.div(
            rx.el.div(rx.el.span(r["role"], style={"fontWeight": 500}), rx.el.span(f"{r['fit']}%  ·  {r['salary']}", class_name="mono ink"), class_name="row between wrap", style={"marginBottom": "8px", "gap": "8px"}),
            bar(r["w"], key=(n == 0)), style={"marginBottom": "18px"},
        ) for n, r in enumerate(c["roles"])],
    )


def extracurricular():
    return profile_strength()


def key_factors():
    return rx.cond(
        State.agent2_ready,
        rx.el.div(
            rx.el.p("SHAP impacts describe the uncalibrated classifier's class 1 output. They do not explain the calibrated estimate or measure admission percentage points.", class_name="body", style={"marginBottom": "20px"}),
            rx.foreach(State.university_factor_rows, lambda f: rx.el.div(
                rx.el.span(f["program"], class_name="body"),
                rx.el.span(f["feature"] + ": " + f["impact"], class_name="mono ink"), class_name="kv-row")),
        ),
        rx.el.p("Agent 2 factors are unavailable until its updated model bundle can be evaluated.", class_name="body"),
    )
