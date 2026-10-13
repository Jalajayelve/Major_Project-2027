import reflex as rx

from ..components.common import label
from ..components.navbar import journey_nav
from ..data import mock
from ..state import State


def _on_change(key: str):
    return lambda v: State.set_field(key, v)


def _field(f: dict):
    key, kind = f["key"], f["kind"]
    if kind == "select":
        opts = list(f["options"])
        control = rx.el.select(
            *[rx.el.option(o or "Select explicitly…", value=o) for o in opts],
            default_value=mock.STUDENT_PROFILE.get(key, opts[0]),
            value=State.profile[key],
            on_change=_on_change(key),
            class_name="input", id=f"f-{key}",
        )
    elif kind == "textarea":
        control = rx.el.textarea(
            default_value=State.profile[key], placeholder=f["placeholder"],
            on_blur=_on_change(key), class_name="input", id=f"f-{key}",
        )
    else:
        # Reflex's number control converts an empty string to 0. Keep raw text
        # so missing evidence stays missing; the service validates the range.
        numeric = {"input_mode": "decimal" if key.endswith("_score") else "numeric"} if kind == "number" else {}
        control = rx.el.input(
            default_value=State.profile[key], placeholder=f["placeholder"], type="text" if kind == "number" else kind,
            on_blur=_on_change(key), class_name="input", id=f"f-{key}",
            **numeric,
        )
    return rx.el.div(
        rx.el.label(f["label"], html_for=f"f-{key}", class_name="field-label"),
        control,
        class_name="field wide" if f["wide"] else "field",
    )


def _panel(i: int, section: dict):
    return rx.cond(
        State.profile_tab == i,
        rx.el.div(
            rx.el.div(
                label(f"Section {i + 1} of {len(mock.FORM_SCHEMA)}", "blue"),
                rx.el.h2(section["label"], class_name="h2", style={"marginTop": "8px"}),
                style={"margin": "8px 0 28px"},
            ),
            rx.el.div(*[_field(f) for f in section["fields"]], class_name="form-grid"),
            *([rx.el.p("Agent 7 requires all eight structured values above. Scores are supplied on a 0–10 rubric scale, not extracted from your documents. Select the applicable degree category and broad field explicitly. Leave unknowns blank; scoring will wait for them. Zero means a known absence. Self-reported inputs are not independently verified.", class_name="body", style={"marginTop": "20px"})] if section["id"] == "experience" else []),
            key=section["id"], class_name="page-enter",
        ),
        rx.fragment(),
    )


_TAB_LABELS = {"tests": "Tests", "goals": "Goals", "intake": "Intake", "programs": "Programs"}


def _tab(i: int, section: dict):
    return rx.el.button(
        f"{i + 1:02d}  {_TAB_LABELS.get(section['id'], section['label'])}",
        on_click=State.set_tab(i), type="button",
        class_name=rx.cond(State.profile_tab == i, "doc-tab active", "doc-tab"),
    )


def _summary():
    return rx.el.aside(
        rx.el.div(
            label("Dossier status", "blue"),
            rx.el.p(State.student_name, class_name="h3", style={"margin": "12px 0 4px"}),
            rx.el.p(State.target_program, class_name="body"),
            rx.el.hr(class_name="rule", style={"margin": "22px 0"}),
            label("Profile complete"),
            rx.el.p(State.completion_str, class_name="num-key", style={"fontSize": "54px", "margin": "8px 0 12px"}),
            rx.el.div(rx.el.i(style={"width": State.completion_str}), class_name="progress"),
            rx.el.p("Optional: IELTS and GMAT. Everything else helps the agents give sharper results.", class_name="body", style={"marginTop": "18px", "fontSize": "13px"}),
            class_name="sheet sheet-pad stacked",
        ),
        style={"position": "sticky", "top": "100px"},
    )


def profile_page():
    return rx.el.div(
        journey_nav(0),
        rx.el.main(
            rx.el.div(
                rx.el.div(
                    label("Step 1 of 4", "blue"),
                    rx.el.h1("Student profile", class_name="h1", style={"marginTop": "10px"}),
                    rx.el.p("Fill in your dossier section by section. Your answers are saved as you move between tabs.", class_name="lede", style={"marginTop": "14px"}),
                    style={"marginBottom": "36px"}, class_name="page-enter",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.div(*[_tab(i, s) for i, s in enumerate(mock.FORM_SCHEMA)], class_name="tabs", role="tablist"),
                        rx.el.div(
                            rx.cond(State.agent7_error != "", rx.el.div(
                                rx.el.p("Your profile has not been submitted yet.", style={"fontWeight": "600"}),
                                rx.el.p(State.agent7_error, class_name="body"),
                                rx.el.p("Correct the required fields using the section tabs, then click Continue to documents again. You do not need to repeat the sections.", class_name="body"),
                                rx.el.button("Review Experience fields", on_click=State.set_tab(next(i for i, s in enumerate(mock.FORM_SCHEMA) if s["id"] == "experience")), type="button", class_name="btn-ghost"),
                                role="alert", custom_attrs={"data-testid": "profile-submission-error"},
                                style={"padding": "20px", "marginBottom": "24px", "border": "1px solid var(--accent)"},
                            ), rx.fragment()),
                            *[_panel(i, s) for i, s in enumerate(mock.FORM_SCHEMA)],
                            rx.el.div(
                                rx.el.button("Back", on_click=State.prev_tab, type="button", class_name="btn-ghost",
                                             style={"visibility": rx.cond(State.profile_tab == 0, "hidden", "visible")}),
                                rx.el.button(
                                    rx.el.span(rx.cond(State.agent7_busy, "Scoring Agent 7…", rx.cond((State.profile_tab == len(mock.FORM_SCHEMA) - 1) | State.profile_submission_attempted, "Continue to documents", "Next section"))),
                                    rx.el.span("→", class_name="tab-arrow"),
                                    on_click=State.next_tab, type="button", class_name="tab-button", disabled=State.agent7_busy,
                                ),
                                class_name="row between", style={"marginTop": "40px", "paddingTop": "24px", "borderTop": "1px solid var(--rule)"},
                            ),
                            class_name="sheet sheet-pad", style={"borderTopLeftRadius": "0", "marginTop": "-1px"},
                        ),
                    ),
                    _summary(),
                    class_name="split", style={"gridTemplateColumns": "minmax(0,2.3fr) minmax(0,1fr)"},
                ),
                class_name="container", style={"padding": "56px 28px 96px"},
            ),
        ),
    )
