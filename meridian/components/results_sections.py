"""Editorial sections shared by the Results dashboard and the Report page."""
import reflex as rx

from ..data import mock
from ..state import State
from .common import bar, count_num, label


def profile_strength():
    ps = mock.PROFILE_STRENGTH
    return rx.el.div(
        rx.el.div(
            label("Overall"),
            count_num(ps["score"], style={"fontSize": "96px", "margin": "6px 0 0"}),
            rx.el.span(f"out of 100 · {ps['label']}", class_name="mono ink"),
        ),
        rx.el.div(
            *[rx.el.div(
                rx.el.div(rx.el.span(d["name"], style={"fontWeight": 500}), rx.el.span(str(d["score"]), class_name="mono ink"), class_name="row between", style={"marginBottom": "8px"}),
                bar(d["pct"], key=(d["score"] == max(x["score"] for x in ps["dimensions"]))),
                style={"marginBottom": "18px"},
            ) for d in ps["dimensions"]],
        ),
        class_name="split", style={"gridTemplateColumns": "minmax(0,1fr) minmax(0,1.6fr)", "gap": "48px"},
    )


def admission_probability():
    rows = []
    for u in sorted(mock.UNIVERSITIES, key=lambda x: -x["prob"]):
        rows.append(rx.el.div(
            rx.el.div(
                rx.el.div(rx.el.span(u["name"], style={"fontWeight": 500}), rx.el.span(u["tier"], class_name="tier"), class_name="row", style={"gap": "12px"}),
                count_num(u["prob"], suffix="%", tag="span", style={"fontSize": "26px"}),
                class_name="row between wrap", style={"marginBottom": "8px", "gap": "8px"},
            ),
            bar(u["prob_str"], key=True), style={"marginBottom": "20px"},
        ))
    return rx.el.div(*rows)


def programs_table():
    head = rx.el.tr(*[rx.el.th(h) for h in ("University", "Program", "Match", "Duration", "Focus")])
    body = [rx.el.tr(
        rx.el.td(p["university"], style={"fontWeight": 500}), rx.el.td(p["program"]),
        rx.el.td(p["match"], class_name="num-key", style={"fontSize": "20px"}), rx.el.td(p["duration"]), rx.el.td(p["focus"]),
    ) for p in mock.PROGRAMS]
    return rx.el.div(rx.el.table(rx.el.thead(head), rx.el.tbody(*body), class_name="plain"), style={"overflowX": "auto"})


def live_programs_table():
    head = rx.el.tr(*[rx.el.th(h) for h in ("University", "Program", "Fit", "Match", "Duration", "Mode")])
    body = rx.foreach(State.program_results, lambda row: rx.el.tr(
            rx.el.td(row["university"], style={"fontWeight": 500}),
            rx.el.td(row["program_name"]),
            rx.el.td(row["specialization_fit_score"], class_name="num-key"),
            rx.el.td(row["match_score"], class_name="num-key"),
            rx.el.td(row["duration"]),
            rx.el.td(row["mode"]),
        ))
    return rx.el.div(
        rx.el.p("Agent 3 program-fit rankings from the saved Agent 2 shortlist. Scores are relevance rankings, not admission probabilities.", class_name="notice"),
        rx.el.table(rx.el.thead(head), rx.el.tbody(body), class_name="plain"),
        style={"overflowX": "auto"},
    )


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


def live_financial():
    return rx.el.div(
        rx.el.p(
            "Agent 4 uses the saved model where its complete feature schema is available; published source rows are shown directly and labeled.",
            class_name="notice",
        ),
        rx.foreach(
            State.financial_results,
            lambda row: rx.el.article(
                rx.el.div(
                    rx.el.span(row["university"], style={"fontWeight": 500}),
                    rx.el.span(row["cost_data_quality"], class_name="mono ink"),
                    class_name="row between wrap", style={"gap": "8px"},
                ),
                rx.el.p(row["program_name"], class_name="body"),
                rx.el.p("Tuition: ", row["currency"], " ", row["tuition_annual"], class_name="mono"),
                rx.el.p("Living: ", row["currency"], " ", row["living_cost_annual"], class_name="mono"),
                rx.el.p("Total annual cost: ", row["currency"], " ", row["total_cost"], class_name="num-key"),
                rx.el.p("Source: ", row["source"], " · Data quality: ", row["cost_data_quality"], class_name="mono"),
                class_name="sheet sheet-pad stacked", style={"marginTop": "14px"},
            ),
        ),
        rx.cond(
            State.financial_skipped.length() > 0,
            rx.el.p(
                "Programs without an exact verified Agent 4 source row were skipped; no costs were inferred for them.",
                class_name="notice", style={"marginTop": "18px"},
            ),
            rx.fragment(),
        ),
    )


def scholarships():
    head = rx.el.tr(*[rx.el.th(h) for h in ("Award", "Type", "Value", "Fit")])
    body = [rx.el.tr(
        rx.el.td(s["name"], style={"fontWeight": 500}), rx.el.td(s["type"]), rx.el.td(s["value"]),
        rx.el.td(rx.el.span(s["fit"], class_name="tier blue" if s["fit"] == "High" else "tier")),
    ) for s in mock.SCHOLARSHIPS]
    return rx.el.div(rx.el.table(rx.el.thead(head), rx.el.tbody(*body), class_name="plain"), style={"overflowX": "auto"})


def live_scholarships():
    def scholarship_card(item):
        return rx.el.article(
            rx.el.div(
                rx.el.h3(item["scholarship_name"], class_name="h3"),
                rx.el.span(item["eligibility_match"], class_name="tier blue"),
                class_name="row between wrap", style={"gap": "12px"},
            ),
            rx.el.p("Potential annual coverage: ", item["potential_annual_coverage"], " ", item["currency"], class_name="num-key"),
            rx.el.p("Catalog match score: ", item["match_score"], " · Deadline: ", item["deadline"], class_name="mono"),
            rx.cond(
                item["source_url"] != "",
                rx.el.a("Verify with provider →", href=item["source_url"], target="_blank", class_name="nav-link"),
                rx.fragment(),
            ),
            class_name="sheet sheet-pad stacked",
        )

    def funding_item(item):
        return rx.el.div(
            rx.el.h3(item["university"], class_name="h3"),
            rx.el.p(item["program_name"], class_name="body"),
            rx.el.p(
                "Funding gap: ",
                rx.cond(item["funding_gap"] != None, item["funding_gap"], "Unknown"),
                " ",
                item["currency"],
                class_name="num-key",
            ),
            rx.el.p(
                "Recommendations",
                class_name="mono",
                style={"marginTop": "14px"},
            ),
            rx.cond(
                item["recommendations"].length() > 0,
                rx.el.div(rx.foreach(item["recommendations"], scholarship_card), class_name="result-list"),
                rx.el.p("No fully eligible catalog recommendations; review the provider-check items below.", class_name="notice"),
            ),
            rx.cond(
                item["eligibility_review"].length() > 0,
                rx.el.div(
                    rx.el.p("Provider-check items", class_name="mono", style={"marginTop": "18px"}),
                    rx.foreach(
                        item["eligibility_review"],
                        lambda review: rx.el.div(
                            rx.el.span(review["scholarship_name"], style={"fontWeight": 500}),
                            rx.el.span(" · ", class_name="mono"),
                            rx.el.span(review["eligibility_match"], class_name="mono blue"),
                            rx.el.p(review["reasons"].to_string(), class_name="body", style={"fontSize": "13px", "marginTop": "4px"}),
                            class_name="kv-row",
                        ),
                    ),
                ),
                rx.fragment(),
            ),
            rx.el.p(
                "Agent 5 uses verified catalog fields and rule-based eligibility. Match scores are retrieval scores, not award probabilities.",
                class_name="notice", style={"marginTop": "14px"},
            ),
            class_name="sheet sheet-pad stacked",
        )

    return rx.el.div(
        rx.el.p(
            "Scholarship recommendations are based on the supplied catalog, explicit eligibility fields, and Agent 4 annual costs. Confirm current rules with each provider.",
            class_name="notice",
        ),
        rx.foreach(State.scholarship_results, funding_item),
    )


def career():
    c = mock.CAREER
    return rx.el.div(
        rx.el.p(c["summary"], class_name="lede", style={"marginBottom": "28px"}),
        *[rx.el.div(
            rx.el.div(rx.el.span(r["role"], style={"fontWeight": 500}), rx.el.span(f"{r['fit']}%  ·  {r['salary']}", class_name="mono ink"), class_name="row between wrap", style={"marginBottom": "8px", "gap": "8px"}),
            bar(r["w"], key=(n == 0)), style={"marginBottom": "18px"},
        ) for n, r in enumerate(c["roles"])],
    )


def live_career():
    return rx.el.div(
        rx.el.p(
            "Agent 6 combines a model-backed earnings estimate with transparent rule-based career alignment.",
            class_name="notice",
        ),
        rx.el.p("Annual earnings model estimate: ", State.career_earnings_estimate, class_name="body"),
        rx.el.h3("Recommended paths", class_name="h3"),
        rx.foreach(State.career_paths, lambda row: rx.el.div(
            rx.el.div(
                rx.el.span(row["career_path"], style={"fontWeight": 500}),
                rx.el.span(row["alignment_score"], "% aligned", class_name="mono ink"),
                class_name="row between wrap", style={"gap": "8px", "marginBottom": "8px"},
            ),
            rx.el.p("Required skills: ", row["required_skills"].to_string(), class_name="body"),
            rx.el.p("Skill gaps: ", row["skill_gaps"].to_string(), class_name="body"),
            class_name="sheet sheet-pad stacked", style={"marginTop": "14px"},
        )),
        rx.el.p(
            "The available earnings artifact produced a model estimate; it is not an observed salary or employment outcome.",
            class_name="notice", style={"marginTop": "18px"},
        ),
    )


def extracurricular():
    e = mock.EXTRACURRICULAR
    return rx.el.div(
        rx.el.div(count_num(e["score"], tag="span", style={"fontSize": "64px"}), rx.el.span("of 100", class_name="mono"), class_name="row", style={"gap": "14px", "alignItems": "baseline", "marginBottom": "24px"}),
        *[rx.el.div(
            rx.el.div(rx.el.span(i["name"], style={"fontWeight": 500}), rx.el.span(str(i["score"]), class_name="mono ink"), class_name="row between", style={"marginBottom": "8px"}),
            bar(i["w"], key=(i["score"] == max(x["score"] for x in e["items"]))), style={"marginBottom": "18px"},
        ) for i in e["items"]],
    )


def live_extracurricular():
    return rx.el.div(
        rx.el.div(
            count_num(State.agent7_score, tag="span", style={"fontSize": "64px"}),
            rx.el.span("of 100", class_name="mono"),
            class_name="row",
            style={"gap": "14px", "alignItems": "baseline", "marginBottom": "24px"},
        ),
        rx.el.div(
            rx.el.span("Strength tier", style={"fontWeight": 500}),
            rx.el.span(State.agent7_tier, class_name="num-key"),
            class_name="row between",
            style={"marginBottom": "12px"},
        ),
        rx.el.div(
            rx.el.span("P(Strong)", style={"fontWeight": 500}),
            rx.el.span(State.agent7_probability, class_name="mono ink"),
            class_name="row between",
            style={"marginBottom": "12px"},
        ),
        rx.el.div(
            rx.el.span("Achievement archetype", style={"fontWeight": 500}),
            rx.el.span("Cluster ", State.agent7_archetype, class_name="mono ink"),
            class_name="row between",
            style={"marginBottom": "12px"},
        ),
        rx.el.p(
            "Research evidence reported: ",
            State.agent7_research_evidence,
            ". P(Strong) is a synthetic strength-class probability, not an admission probability.",
            class_name="notice",
        ),
    )


def key_factors():
    rows = []
    for k in mock.KEY_FACTORS:
        rows.append(rx.el.div(
            rx.el.div(rx.el.span(k["name"], style={"fontWeight": 500}),
                      rx.el.span(k["impact"], class_name="num-key" if k["positive"] else "mono ink", style={"fontSize": "22px"} if k["positive"] else {}),
                      class_name="row between", style={"marginBottom": "8px", "gap": "12px"}),
            bar(k["w"], key=k["positive"], neg=not k["positive"]), style={"marginBottom": "18px"},
        ))
    return rx.el.div(
        rx.el.p("Blue bars raised your estimate; grey bars lowered it. Points show the approximate effect on your overall admission outlook.", class_name="body", style={"marginBottom": "24px"}),
        *rows,
    )
