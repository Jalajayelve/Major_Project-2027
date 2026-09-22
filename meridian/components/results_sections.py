"""Editorial sections shared by the Results dashboard and the Report page."""
import reflex as rx

from ..data import mock
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
    e = mock.EXTRACURRICULAR
    return rx.el.div(
        rx.el.div(count_num(e["score"], tag="span", style={"fontSize": "64px"}), rx.el.span("of 100", class_name="mono"), class_name="row", style={"gap": "14px", "alignItems": "baseline", "marginBottom": "24px"}),
        *[rx.el.div(
            rx.el.div(rx.el.span(i["name"], style={"fontWeight": 500}), rx.el.span(str(i["score"]), class_name="mono ink"), class_name="row between", style={"marginBottom": "8px"}),
            bar(i["w"], key=(i["score"] == max(x["score"] for x in e["items"]))), style={"marginBottom": "18px"},
        ) for i in e["items"]],
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
