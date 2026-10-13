"""Render the final report to PDF (ReportLab). Colours come from theme.py."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle

from .. import theme as T

INK, NAVY, IVORY = HexColor(T.INK), HexColor(T.NAVY), HexColor(T.IVORY)
PAPER, SLATE, ACCENT, ACCENT_DEEP = HexColor(T.PAPER), HexColor(T.SLATE), HexColor(T.ACCENT), HexColor(T.ACCENT_DEEP)

_LOGO = ImageReader(str(Path(__file__).with_name("logo_ivory.png")))

_S = {
    "h": ParagraphStyle("h", fontName="Times-Bold", fontSize=17, leading=20, textColor=INK, spaceBefore=2, spaceAfter=4),
    "eyebrow": ParagraphStyle("e", fontName="Courier-Bold", fontSize=7.5, leading=10, textColor=ACCENT_DEEP, spaceBefore=16, spaceAfter=2),
    "body": ParagraphStyle("b", fontName="Helvetica", fontSize=9.5, leading=14, textColor=INK, alignment=TA_LEFT),
    "cell": ParagraphStyle("c", fontName="Helvetica", fontSize=9, leading=12, textColor=INK),
    "head": ParagraphStyle("th", fontName="Courier-Bold", fontSize=7, leading=9, textColor=SLATE),
    "key": ParagraphStyle("k", fontName="Times-Bold", fontSize=30, leading=34, textColor=ACCENT_DEEP),
}


def _page(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(IVORY); canvas.rect(0, 0, w, h, stroke=0, fill=1)
    canvas.setFillColor(NAVY); canvas.rect(0, h - 22 * mm, w, 22 * mm, stroke=0, fill=1)
    canvas.setFillColor(ACCENT); canvas.rect(0, h - 22 * mm, w, 1.2 * mm, stroke=0, fill=1)
    lw = 34 * mm
    canvas.drawImage(_LOGO, 20 * mm, h - 16.5 * mm, width=lw, height=lw * 637 / 2524, mask="auto")
    canvas.setFont("Courier", 7.5); canvas.setFillColor(PAPER)
    canvas.drawRightString(w - 20 * mm, h - 14 * mm, "STUDY ABROAD REPORT")
    canvas.setFillColor(SLATE); canvas.setFont("Courier", 7)
    canvas.drawString(20 * mm, 10 * mm, f"REPORT NO. {doc.report_no}")
    canvas.drawRightString(w - 20 * mm, 10 * mm, f"PAGE {doc.page}")
    canvas.restoreState()


def _section(title: str, no: str):
    return [Paragraph(f"SECTION {no}", _S["eyebrow"]), Paragraph(title, _S["h"])]


def _table(rows, widths, head=True):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    style = [("LINEBELOW", (0, 0), (-1, -1), 0.3, SLATE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]
    if head:
        style.append(("LINEBELOW", (0, 0), (-1, 0), 0.8, INK))
    t.setStyle(TableStyle(style))
    return t


def render_report_pdf(report: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, title="Meridian Study Abroad Report", author="Meridian")
    doc.report_no = report["student"]["report_no"]
    w, h = A4
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(20 * mm, 16 * mm, w - 40 * mm, h - 44 * mm, id="f")], onPage=_page)])
    s = report["student"]
    P = lambda t, st="cell": Paragraph(escape(str(t)), _S[st])  # noqa: E731
    H = lambda t: Paragraph(t, _S["head"])  # noqa: E731
    W = w - 40 * mm
    el = [Spacer(1, 4 * mm), Paragraph("YOUR PERSONAL DOSSIER", _S["eyebrow"]),
          Paragraph(escape(s["name"]), ParagraphStyle("n", fontName="Times-Bold", fontSize=30, leading=34, textColor=INK)), Spacer(1, 3 * mm),
          _table([[H("TARGET"), H("PROGRAM"), H("INTAKE")], [P(s["target"]), P(s["program"]), P(s["intake"])]], [W / 3] * 3)]

    el += [P("Agent 7 uses real model inference. Agent 2 results require its complete updated bundle. Program, financial, scholarship and career sections below remain demonstration data.", "body")]
    ps = report["profile_strength"]
    el += _section("Profile strength", "01")
    el += [Paragraph(f"{ps['score']} / 100 - {ps['label']}", _S["key"]), Spacer(1, 2 * mm),
           _table([[H("DIMENSION"), H("SCORE")]] + [[P(d["name"]), P(d["score"])] for d in ps["dimensions"]], [W * .7, W * .3])]

    if report.get("agent7_notice"):
        el += [P(report["agent7_notice"], "body")]

    el += _section("University recommendations", "02")
    if report.get("agent2_notice"):
        el += [P(report["agent2_notice"], "body"), Spacer(1, 2 * mm)]
    el += [_table([[H("UNIVERSITY"), H("PROGRAM"), H("EXPERIMENTAL BAND"), H("UNVALIDATED MODEL SCORE"), H("TUITION")]] +
                  [[P(u["name"]), P(u["program"] + (" — " + u["evidence_reason"] if u.get("evidence_reason") else "")), P(u["tier"]), P(u["prob_str"]), P(u["tuition_str"])] for u in report["universities"]],
                  [W * .32, W * .26, W * .14, W * .12, W * .16])]
    if not report["universities"]:
        el += [P("Run analysis to generate current experimental matches and scores.", "body")]

    el += _section("Program matches - demonstration", "03")
    el += [_table([[H("UNIVERSITY"), H("PROGRAM"), H("MATCH"), H("DURATION")]] +
                  [[P(p["university"]), P(p["program"]), P(p["match"]), P(p["duration"])] for p in report["programs"]],
                  [W * .22, W * .38, W * .14, W * .26])]

    f = report["financial"]
    el += _section("Cost breakdown - demonstration", "04")
    el += [Paragraph(f"{f['total_str']} per year", _S["key"]), P(f"Budget {f['budget_str']}  |  {f['gap_str']}"), Spacer(1, 2 * mm),
           _table([[H("ITEM"), H("ESTIMATE")]] + [[P(i["name"]), P(i["amount"])] for i in f["items"]], [W * .7, W * .3])]

    el += _section("Scholarships - demonstration", "05")
    el += [_table([[H("AWARD"), H("VALUE"), H("FIT")]] + [[P(x["name"]), P(x["value"]), P(x["fit"])] for x in report["scholarships"]],
                  [W * .5, W * .32, W * .18])]

    c = report["career"]
    el += _section("Career alignment - demonstration", "06")
    el += [P(c["summary"], "body"), Spacer(1, 2 * mm),
           _table([[H("ROLE"), H("FIT"), H("SALARY RANGE")]] + [[P(r["role"]), P(f"{r['fit']}%"), P(r["salary"])] for r in c["roles"]],
                  [W * .5, W * .15, W * .35])]

    e = report["extracurricular"]
    el += _section("Extracurricular strength", "07")
    el += [_table([[H("AREA"), H("SCORE")]] + [[P(i["name"]), P(i["score"])] for i in e["items"]], [W * .7, W * .3])]

    el += _section("Key model factors", "08")
    el += [P("SHAP factors, when available, describe the uncalibrated classifier. They do not explain the calibrated estimate or measure admission percentage points.", "body")]
    el += [_table([[H("FACTOR"), H("IMPACT")]] + [[P(k["name"]), P(k["impact"])] for k in report["key_factors"]], [W * .75, W * .25]),
           Spacer(1, 4 * mm), P("Figures are illustrative estimates generated for demonstration and are not a guarantee of admission or funding.", "body")]
    doc.build(el)
    return buf.getvalue()
