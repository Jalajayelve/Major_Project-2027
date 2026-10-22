import reflex as rx

from ..components.common import label, primary_button
from ..components.navbar import journey_nav
from ..data import mock
from ..state import State
from .account import notice

_HANDLERS = {
    "resume": State.upload_resume, "transcript": State.upload_transcript,
    "sop": State.upload_sop, "lor": State.upload_lor, "other": State.upload_other,
}


def _slot(d: dict):
    slot, uid = d["slot"], f"up_{d['slot']}"
    empty = rx.el.div(
        label(d["label"], "ink"),
        rx.el.p("Document upload not connected", class_name="serif", style={"fontSize": "20px", "fontWeight": 600, "margin": "6px 0 2px"}),
        rx.el.span("Formats and size limits will be published when the processing API is connected.", style={"fontSize": "13px", "color": "var(--ink-soft)"}),
        class_name="drop",
    )
    filled = rx.el.div(
        rx.el.div(State.docs[f"{slot}_type"], class_name="file-badge"),
        rx.el.div(
            label(d["label"], "blue"),
            rx.el.p(State.docs[f"{slot}_name"], class_name="trunc", style={"margin": "6px 0 4px", "fontWeight": 600}),
            rx.el.div(
                rx.el.span(State.docs[f"{slot}_size"], class_name="mono"),
                rx.el.span("âœ“ Received", class_name="mono blue", style={"fontWeight": 600}),
                class_name="row", style={"gap": "16px"},
            ),
            style={"minWidth": 0},
        ),
        class_name="doc-card",
    )
    return rx.el.div(
        rx.upload.root(
            rx.cond(State.uploaded_slots.contains(slot), filled, empty),
            id=uid, max_files=1, multiple=False, disabled=True,
            accept={"application/pdf": [".pdf"], "application/msword": [".doc"],
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                    "text/plain": [".txt"], "image/*": [".png", ".jpg", ".jpeg"]},
            on_drop=_HANDLERS[slot](rx.upload_files(upload_id=uid)),
            class_name="upload-root",
        ),
        rx.cond(
            State.uploaded_slots.contains(slot),
            rx.el.button("Replace or remove", on_click=State.remove_document(slot), type="button", class_name="nav-link",
                         style={"background": "none", "border": 0, "cursor": "pointer", "marginTop": "10px", "color": "var(--accent-deep)"}),
            rx.fragment(),
        ),
    )


def documents_page():
    return rx.el.div(
        journey_nav(1),
        notice(),
        rx.el.main(
            rx.el.div(
                rx.el.div(
                    label("Step 2 of 4", "blue"),
                    rx.el.h1("Admissions desk", class_name="h1", style={"marginTop": "10px"}),
                    rx.el.p("Document processing is unavailable. No upload, OCR, extraction, or confirmation endpoint exists in the backend. Files are not stored; you can continue with your profile.", class_name="lede", style={"marginTop": "14px"}),
                    class_name="page-enter", style={"marginBottom": "40px"},
                ),
                rx.el.div(
                    rx.el.div(*[_slot(d) for d in mock.DOC_SLOTS], class_name="grid-2"),
                    class_name="sheet sheet-pad stacked", style={"background": "var(--paper)"},
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.span(State.docs_count, class_name="num-key", style={"fontSize": "40px"}),
                        rx.el.span(f" of {len(mock.DOC_SLOTS)} documents received", class_name="mono"),
                        class_name="row", style={"gap": "10px", "alignItems": "baseline"},
                    ),
                    rx.el.div(

                        primary_button("Start analysis", rx.redirect("/analysis")),
                        class_name="row wrap", style={"gap": "16px"},
                    ),
                    class_name="row wrap between", style={"gap": "20px", "marginTop": "36px"},
                ),
                class_name="container", style={"padding": "56px 28px 96px"},
            ),
        ),
    )
