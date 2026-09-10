import asyncio

import reflex as rx

from .engine import agent_result, profile_score, universities_for


AGENT_FLOW = [
    ("Profile Compass", "01", "Build the shared student context", "◎"),
    ("University Matcher", "02", "Validate your university strategy", "◈"),
    ("Program Architect", "03", "Find the right course and specialisation", "⌘"),
    ("Finance Planner", "04", "Plan costs and funding gap", "◇"),
    ("Scholarship Finder", "05", "Surface funding opportunities", "✦"),
    ("Career Navigator", "06", "Connect study to career outcomes", "↗"),
    ("Documents Coach", "07", "Strengthen every application document", "▣"),
]

AGENT_EXAMPLES = {
    "Profile Compass": "e.g. Which part of my profile needs the most improvement?",
    "University Matcher": "e.g. Should I keep a safe university in my shortlist?",
    "Program Architect": "e.g. Which Master’s specialisation fits a data analyst career?",
    "Finance Planner": "e.g. What should I include in my U.S. study budget?",
    "Scholarship Finder": "e.g. Which documents can strengthen my scholarship application?",
    "Career Navigator": "e.g. Which U.S. programme has the best internship pathway?",
    "Documents Coach": "e.g. What should my SOP say about my career goal?",
}


class State(rx.State):
    """All UI state; swap engine calls for a FastAPI/LangGraph client in production."""

    screen: str = "auth"
    auth_mode: str = "signup"
    email: str = ""
    password: str = ""
    account_name: str = ""
    auth_error: str = ""

    full_name: str = ""
    country: str = ""
    degree: str = "Masters"
    nationality: str = ""
    previous_degree: str = ""
    graduation_year: str = ""
    field: str = ""
    target_country: str = "United States"
    intake: str = ""
    gpa: str = ""
    english_score: str = ""
    english_test: str = "IELTS"
    gre_score: str = ""
    experience_years: str = "0"
    budget: str = ""
    funding_source: str = ""
    career_goal: str = ""
    work_background: str = ""
    activities: str = ""
    research: str = ""
    sop: str = ""
    documents_ready: str = ""

    progress: int = 0
    pipeline_stage: int = 0
    pipeline_label: str = "Preparing your shared student context"
    running: bool = False
    tier: str = ""
    score: int = 0
    tier_message: str = ""
    recommendations: list[dict[str, str]] = []
    agent_index: int = 0
    agent_number: str = "01"
    selected_agent: str = "Profile Compass"
    agent_description: str = "Build the shared student context"
    agent_icon: str = "◎"
    agent_placeholder: str = "e.g. Which part of my profile needs the most improvement?"
    agent_question: str = ""
    agent_reply: str = ""
    agent_bullets: list[str] = []
    agent_summaries: list[dict[str, str]] = []
    current_agent_complete: bool = False

    def set_auth_mode(self, mode: str):
        self.auth_mode = mode
        self.auth_error = ""

    def submit_auth(self):
        if not self.email.strip() or not self.password.strip():
            self.auth_error = "Enter an email address and password to continue."
            return
        if not self.account_name.strip():
            self.account_name = self.email.split("@")[0].replace(".", " ").title()
        self.auth_error = ""
        self.screen = "profile"

    def update_field(self, field_name: str, value: str):
        setattr(self, field_name, value)

    def _profile(self) -> dict[str, str]:
        return {
            "gpa": self.gpa, "english_score": self.english_score,
            "experience_years": self.experience_years, "sop": self.sop,
            "activities": self.activities, "country": self.country,
            "field": self.field, "degree": self.degree, "budget": self.budget,
            "career_goal": self.career_goal,
        }

    async def run_pipeline(self):
        required = [self.full_name, self.country, self.field, self.intake, self.gpa, self.english_score, self.gre_score]
        if not all(value.strip() for value in required):
            test_name = "GMAT" if self.degree == "MBA" else "GRE"
            self.auth_error = f"Please complete name, country, field, intake, GPA, English score and {test_name} score."
            return
        self.auth_error = ""
        self.running = True
        self.screen = "pipeline"
        self.progress = 15
        self.pipeline_stage = 1
        self.pipeline_label = "Profile Agent is reading your academic and test profile"
        yield
        await asyncio.sleep(0.7)
        profile = self._profile()
        self.progress = 32
        self.score, self.tier, self.tier_message = profile_score(profile)
        self.pipeline_stage = 2
        self.pipeline_label = "University Agent is matching U.S. universities"
        yield
        await asyncio.sleep(0.7)
        self.progress = 54
        self.recommendations = universities_for(profile, self.tier)
        self.pipeline_stage = 3
        self.pipeline_label = "Program and Finance Agents are comparing your options"
        yield
        await asyncio.sleep(0.7)
        self.progress = 75
        self.pipeline_stage = 4
        self.pipeline_label = "Scholarship, Career and Documents Agents are preparing your plan"
        yield
        await asyncio.sleep(0.7)
        self.progress = 100
        self.pipeline_stage = 5
        self.pipeline_label = "Your personalised U.S. application route is ready"
        yield
        await asyncio.sleep(0.6)
        self.running = False
        self.screen = "tier"

    def go_to_profile(self):
        self.screen = "profile"
        self.auth_error = ""

    def start_agent_flow(self):
        self.agent_index = 0
        self.agent_number = "01"
        self.selected_agent = "Profile Compass"
        self.agent_description = "Build the shared student context"
        self.agent_icon = "◎"
        self.agent_placeholder = AGENT_EXAMPLES["Profile Compass"]
        self.agent_question = ""
        self.agent_reply = ""
        self.agent_bullets = []
        self.agent_summaries = []
        self.current_agent_complete = False
        self.screen = "advisor"

    def ask_agent(self):
        output = agent_result(self.selected_agent, self.agent_question, self._profile(), self.tier)
        self.agent_reply = str(output["summary"])
        self.agent_bullets = list(output["bullets"])
        self.current_agent_complete = True
        entry = {"name": self.selected_agent, "number": self.agent_number, "summary": self.agent_reply, "details": "\n".join(f"• {bullet}" for bullet in self.agent_bullets)}
        self.agent_summaries = [item for item in self.agent_summaries if item["name"] != self.selected_agent] + [entry]

    def next_agent(self):
        if not self.current_agent_complete:
            self.ask_agent()
        if self.agent_index >= len(AGENT_FLOW) - 1:
            self.screen = "report"
            return
        self.agent_index += 1
        name, number, description, icon = AGENT_FLOW[self.agent_index]
        self.selected_agent = name
        self.agent_number = number
        self.agent_description = description
        self.agent_icon = icon
        self.agent_placeholder = AGENT_EXAMPLES[name]
        self.agent_question = ""
        self.agent_reply = ""
        self.agent_bullets = []
        self.current_agent_complete = False

    def previous_agent(self):
        if self.agent_index == 0:
            self.screen = "tier"
            return
        self.agent_index -= 1
        name, number, description, icon = AGENT_FLOW[self.agent_index]
        self.selected_agent = name
        self.agent_number = number
        self.agent_description = description
        self.agent_icon = icon
        self.agent_placeholder = AGENT_EXAMPLES[name]
        self.agent_question = ""
        self.agent_reply = ""
        self.agent_bullets = []
        self.current_agent_complete = False

    def download_report(self):
        colleges = "\n".join(f"• {item['name']} ({item['country']}) — {item['chance']} estimated match" for item in self.recommendations)
        agent_notes = "\n".join(f"\n{item['number']} {item['name']}\n{item['summary']}\n{item['details']}" for item in self.agent_summaries)
        report = f"""STUDYPATH — STUDY ABROAD ELIGIBILITY REPORT
Prepared for: {self.full_name}
Programme goal: {self.degree} in {self.field}
Target intake: {self.intake}

PROFILE RESULT
Tier: {self.tier}
Readiness score: {self.score}/100
Assessment: {self.tier_message}

UNIVERSITY MATCHES
{colleges}

SEVEN-AGENT COUNSELLING SUMMARY
{agent_notes}

This report is a planning aid. Admission, scholarship and visa decisions remain with the relevant university and authorities.
"""
        return rx.download(data=report, filename="StudyPath-Eligibility-Report.txt")


def brand() -> rx.Component:
    return rx.hstack(
        rx.box("S", class_name="brand-mark"),
        rx.vstack(rx.text("StudyPath", class_name="brand-name"), rx.text("YOUR GLOBAL EDUCATION COMPASS", class_name="brand-subtitle"), spacing="0"),
        spacing="3",
        align="center",
    )


def field_input(label: str, state_field: str, placeholder: str, input_type: str = "text") -> rx.Component:
    return rx.vstack(
        rx.text(label, class_name="field-label"),
        rx.input(
            value=getattr(State, state_field),
            placeholder=placeholder,
            type=input_type,
            on_change=lambda value: State.update_field(state_field, value),
            class_name="text-input",
        ),
        spacing="1",
        width="100%",
    )


def select_input(label: str, state_field: str, options: list[str]) -> rx.Component:
    return rx.vstack(
        rx.text(label, class_name="field-label"),
        rx.select(options, value=getattr(State, state_field), on_change=lambda value: State.update_field(state_field, value), class_name="select-input"),
        spacing="1", width="100%",
    )


def text_area(label: str, state_field: str, placeholder: str) -> rx.Component:
    return rx.vstack(
        rx.text(label, class_name="field-label"),
        rx.text_area(value=getattr(State, state_field), placeholder=placeholder, on_change=lambda value: State.update_field(state_field, value), class_name="text-area"),
        spacing="1", width="100%",
    )


def auth_page() -> rx.Component:
    return rx.box(
        rx.box(class_name="orb orb-one"), rx.box(class_name="orb orb-two"), rx.box(class_name="orb orb-three"),
        rx.box(
            rx.hstack(brand(), rx.text("Your future, mapped with clarity.", class_name="auth-nav-copy"), justify="between", align="center", class_name="auth-nav"),
            rx.flex(
                rx.vstack(
                    rx.text("STUDY ABROAD, REIMAGINED", class_name="hero-kicker"),
                    rx.heading("A clearer way to find your place in the world.", class_name="hero-title"),
                    rx.text("Move from profile to university, scholarship and application plan through one intelligent, visual journey.", class_name="hero-copy"),
                    rx.hstack(rx.box("7", class_name="stat-number"), rx.text("specialist agents, one shared student story", class_name="stat-copy"), spacing="4", align="center"),
                    rx.box(
                        rx.text("HOW STUDYPATH HELPS", class_name="about-kicker"),
                        rx.text("A practical plan for every important decision.", class_name="about-title"),
                        rx.vstack(
                            rx.hstack(rx.text("01", class_name="about-number"), rx.vstack(rx.text("Find better-fit universities", class_name="about-item-title"), rx.text("Balance reach, target and safe options around your profile.", class_name="about-item-copy"), spacing="1", align="start"), spacing="3", align="start"),
                            rx.hstack(rx.text("02", class_name="about-number"), rx.vstack(rx.text("Plan the real cost", class_name="about-item-title"), rx.text("Compare tuition, living costs and funding routes before you commit.", class_name="about-item-copy"), spacing="1", align="start"), spacing="3", align="start"),
                            rx.hstack(rx.text("03", class_name="about-number"), rx.vstack(rx.text("Strengthen your application", class_name="about-item-title"), rx.text("Turn your documents, goals and experience into clear next steps.", class_name="about-item-copy"), spacing="1", align="start"), spacing="3", align="start"),
                            spacing="3",
                        ),
                        class_name="about-panel",
                    ),
                    rx.box(rx.box(class_name="orbit orbit-a"), rx.box(class_name="orbit orbit-b"), rx.box(rx.box(class_name="globe-meridian"), rx.box(class_name="globe-latitude latitude-one"), rx.box(class_name="globe-latitude latitude-two"), rx.text("✦", class_name="globe-star star-one"), rx.text("✦", class_name="globe-star star-two"), class_name="globe"), rx.box("CANADA", class_name="map-tag tag-one"), rx.box("UK", class_name="map-tag tag-two"), rx.box("AU", class_name="map-tag tag-three"), class_name="globe-stage"),
                    spacing="5", class_name="auth-hero", align="start",
                ),
                rx.box(rx.vstack(
                    rx.text("WELCOME ABOARD", class_name="eyebrow"),
                    rx.text("Start your application journey", class_name="auth-title"),
                    rx.text("Create a private planning space. Your profile unlocks a personalised route forward.", class_name="muted"),
                    rx.hstack(rx.button("Create account", on_click=lambda: State.set_auth_mode("signup"), class_name=rx.cond(State.auth_mode == "signup", "tab active-tab", "tab")), rx.button("Log in", on_click=lambda: State.set_auth_mode("login"), class_name=rx.cond(State.auth_mode == "login", "tab active-tab", "tab")), width="100%", class_name="auth-tabs"),
                    rx.cond(State.auth_mode == "signup", field_input("Your name", "account_name", "e.g. Aanya Sharma"), rx.fragment()),
                    field_input("Email address", "email", "you@example.com", "email"),
                    field_input("Password", "password", "Create a secure password", "password"),
                    rx.cond(State.auth_error != "", rx.text(State.auth_error, class_name="error-text"), rx.fragment()),
                    rx.button(rx.cond(State.auth_mode == "signup", "Create my study plan  →", "Continue to my profile  →"), on_click=State.submit_auth, class_name="primary-button", width="100%"),
                    rx.text("Prototype mode · your information remains in this session.", class_name="fine-print"),
                    spacing="5", width="100%",
                ), class_name="auth-card"),
                direction=rx.breakpoints(initial="column", lg="row"), align="center", justify="between", gap="60px", class_name="auth-layout",
            ), class_name="auth-shell",
        ),
        class_name="page auth-page",
    )


def profile_page() -> rx.Component:
    return rx.box(
        navbar("Your profile", "Step 1 of 3"),
        rx.container(
            rx.vstack(
                rx.box(
                    rx.text("PROFILE EVALUATION", class_name="eyebrow"),
                    rx.text("The details that make your plan yours.", class_name="page-title"),
                    rx.text("The profile agent uses these signals to create your shared counselling context. Fill in what you know now — you can return and refine it later.", class_name="muted intro-copy"),
                    rx.box(
                        rx.text("What to prepare", class_name="profile-guide-title"),
                        rx.text("Use the examples inside each field as a guide. You can enter approximate information now and update your profile later.", class_name="profile-guide-copy"),
                        rx.hstack(
                            rx.text("Academic history", class_name="profile-guide-item"),
                            rx.text("Test scores", class_name="profile-guide-item"),
                            rx.text("Goals and experience", class_name="profile-guide-item"),
                            spacing="3", wrap="wrap",
                        ),
                        class_name="profile-guide",
                    ),
                    class_name="intro",
                ),
                rx.box(
                    rx.vstack(
                        rx.hstack(rx.box("01", class_name="section-number"), rx.vstack(rx.text("Identity & study direction", class_name="section-title"), rx.text("Your starting point and the course you are aiming for.", class_name="muted small"), spacing="1", align="start"), align="center", spacing="3"),
                        rx.grid(
                            field_input("Full name *", "full_name", "Your full name"),
                            field_input("Current country *", "country", "e.g. India"),
                            field_input("Nationality", "nationality", "e.g. Indian"),
                            select_input("Programme type", "degree", ["Masters", "MBA"]),
                            field_input("Field of study *", "field", "e.g. Data Science"),
                            field_input("Preferred U.S. state / city", "target_country", "e.g. California or Boston"),
                            field_input("Target intake", "intake", "e.g. Fall 2027"),
                            columns=rx.breakpoints(initial="1", md="2"),
                            spacing="5",
                            width="100%",
                        ),
                        rx.divider(),
                        rx.hstack(rx.box("02", class_name="section-number"), rx.vstack(rx.text("Academic & test profile", class_name="section-title"), rx.text("The measurable signals universities assess.", class_name="muted small"), spacing="1", align="start"), align="center", spacing="3"),
                        rx.grid(
                            field_input("Previous degree", "previous_degree", "e.g. B.Tech in Computer Science"),
                            field_input("Graduation year", "graduation_year", "e.g. 2025"),
                            field_input("GPA / percentage *", "gpa", "e.g. 8.2"),
                            select_input("English test", "english_test", ["IELTS", "TOEFL", "PTE", "Duolingo", "Not taken yet"]),
                            field_input("English score *", "english_score", "e.g. 7.5"),
                            rx.cond(State.degree == "MBA", field_input("GMAT score *", "gre_score", "e.g. 650"), field_input("GRE score *", "gre_score", "e.g. 320")),
                            field_input("Work experience (years)", "experience_years", "0"),
                            field_input("Annual budget (optional)", "budget", "e.g. $35,000"),
                            columns=rx.breakpoints(initial="1", md="2"), spacing="5", width="100%",
                        ),
                        rx.divider(),
                        rx.hstack(rx.box("03", class_name="section-number"), rx.vstack(rx.text("Career, budget & evidence", class_name="section-title"), rx.text("The context used by finance, career and scholarship agents.", class_name="muted small"), spacing="1", align="start"), align="center", spacing="3"),
                        rx.grid(field_input("Funding source", "funding_source", "Family, loan, savings, sponsor"), field_input("Career goal", "career_goal", "e.g. Product data analyst"), columns=rx.breakpoints(initial="1", md="2"), spacing="5", width="100%"),
                        text_area("Work experience / internships", "work_background", "Role, employer, skills and achievements"),
                        text_area("Activities, leadership or volunteering", "activities", "Clubs, volunteering, competitions, leadership or social impact"),
                        text_area("Research, projects, publications or patents", "research", "Research papers, projects, GitHub work, conferences or awards"),
                        text_area("SOP / personal motivation notes", "sop", "Why this course, what you have done, and what you want to achieve"),
                        text_area("Documents already ready", "documents_ready", "Passport, transcripts, test results, CV, LORs, financial documents"),
                        rx.cond(State.auth_error != "", rx.text(State.auth_error, class_name="error-text"), rx.fragment()),
                        rx.button("Run my U.S. admissions pipeline  →", on_click=State.run_pipeline, class_name="primary-button", width="100%"),
                        spacing="5", width="100%",
                    ), class_name="content-card",
                ),
            ), spacing="6", padding_y="42px", width="100%",
        ), class_name="page",
    )


def pipeline_node(number: str, label: str, stage: int) -> rx.Component:
    return rx.box(
        rx.box(number, class_name="pipeline-node-number"),
        rx.text(label, class_name="pipeline-node-label"),
        class_name=rx.cond(State.pipeline_stage >= stage, "pipeline-node pipeline-node-live", "pipeline-node"),
    )


def pipeline_page() -> rx.Component:
    return rx.box(
        navbar("Building your U.S. admissions route", "ANALYSING"),
        rx.center(
            rx.vstack(
                rx.text("LIVE COUNSELLING PIPELINE", class_name="eyebrow"),
                rx.text("Your plan is taking shape.", class_name="page-title pipeline-title"),
                rx.text(State.pipeline_label, class_name="pipeline-label"),
                rx.box(
                    rx.box(class_name="pipeline-orbit pipeline-orbit-one"),
                    rx.box(class_name="pipeline-orbit pipeline-orbit-two"),
                    rx.box("✦", class_name="pipeline-spark spark-a"),
                    rx.box("✦", class_name="pipeline-spark spark-b"),
                    rx.box(rx.text("US", class_name="pipeline-core-text"), class_name="pipeline-core"),
                    class_name="pipeline-visual",
                ),
                rx.progress(value=State.progress, color_scheme="cyan", class_name="pipeline-progress"),
                rx.text(State.progress.to_string() + "% complete", class_name="fine-print"),
                rx.grid(
                    pipeline_node("01", "Profile", 1), pipeline_node("02", "University", 2), pipeline_node("03", "Program", 3), pipeline_node("04", "Finance", 3), pipeline_node("05", "Scholarship", 4), pipeline_node("06", "Career", 4), pipeline_node("07", "Documents", 4),
                    columns=rx.breakpoints(initial="2", sm="4", md="7"), spacing="3", width="100%", class_name="pipeline-nodes",
                ),
                rx.text("Your academic profile, test score, U.S. programme choices and finances are being considered together.", class_name="muted pipeline-note"),
                spacing="4", align="center", width="min(100%, 820px)", class_name="pipeline-card",
            ),
            padding="48px 20px", min_height="calc(100vh - 76px)",
        ), class_name="page pipeline-page",
    )


def navbar(title: str, step: str) -> rx.Component:
    return rx.box(
        rx.container(rx.hstack(brand(), rx.hstack(rx.text(title, class_name="nav-title"), rx.badge(step, class_name="step-badge"), spacing="3", align="center"), justify="between", align="center", padding_y="18px")),
        class_name="navbar",
    )


def university_card(item: dict[str, str]) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(rx.text(item["name"][0], class_name="uni-letter"), class_name="uni-logo"),
            rx.vstack(rx.text(item["name"], class_name="uni-name"), rx.text(item["country"] + " · " + item["program"], class_name="muted small"), spacing="1", align="start", width="100%"),
            rx.vstack(rx.badge(item["category"], class_name="match-badge"), rx.text(item["chance"] + " match", class_name="chance"), spacing="1", align="end"),
            width="100%", align="center",
        ),
        rx.text(item["note"], class_name="card-note"),
        class_name="university-card",
    )


def tier_page() -> rx.Component:
    return rx.box(
        navbar("Tier & university match", "02 / 03"),
        rx.container(
            rx.vstack(
                rx.box(
                    rx.text("Your route is starting to take shape.", class_name="page-title"),
                    rx.text("Your tier is an explainable readiness view — it helps balance ambition with options.", class_name="muted intro-copy"),
                    class_name="intro",
                ),
                rx.box(
                    rx.box(class_name="tier-glow"),
                    rx.text("PROFILE READINESS", class_name="eyebrow"),
                    rx.hstack(rx.vstack(rx.text(State.tier, class_name="tier-title"), rx.text(State.tier_message, class_name="muted"), align="start", spacing="2"), rx.vstack(rx.text(State.score.to_string(), class_name="score"), rx.text("profile score / 100", class_name="fine-print"), align="end", spacing="0"), justify="between", width="100%"),
                    rx.progress(value=State.score, color_scheme="cyan", class_name="score-progress"),
                    rx.hstack(rx.text("Academic fit", class_name="metric"), rx.text("Language readiness", class_name="metric"), rx.text("Profile evidence", class_name="metric"), wrap="wrap", margin_top="22px", spacing="3"),
                    class_name="tier-card",
                ),
                rx.box(
                    rx.hstack(rx.vstack(rx.text("Your university shortlist", class_name="section-title"), rx.text("Each confidence score is an estimate from your current profile, not an admission guarantee.", class_name="muted"), spacing="1", align="start"), rx.button("Edit profile", on_click=State.go_to_profile, class_name="ghost-button"), justify="between", align="center", width="100%"),
                    rx.vstack(rx.foreach(State.recommendations, university_card), spacing="3", width="100%", margin_top="22px"),
                    class_name="content-card",
                ),
                rx.box(
                    rx.hstack(rx.vstack(rx.text("Continue with your complete plan", class_name="section-title"), rx.text("Next, the seven specialist agents will give you one focused result at a time — scholarship, documents, finance and more.", class_name="muted small"), spacing="1", align="start"), rx.button("Start 7-agent plan  →", on_click=State.start_agent_flow, class_name="primary-button"), justify="between", align="center", width="100%"), class_name="submit-panel",
                ),
                spacing="5", padding_y="42px", width="100%",
            ),
        ), class_name="page",
    )


def advisor_page() -> rx.Component:
    return rx.box(
        navbar("Guided counselling plan", "03 / 03"),
        rx.container(
            rx.vstack(
                rx.hstack(rx.button("← University matches", on_click=State.previous_agent, class_name="back-button"), rx.text("AGENT " + State.agent_number + " / 07", class_name="agent-position"), justify="between", width="100%"),
                rx.hstack(rx.box(State.agent_icon, class_name="agent-orb"), rx.vstack(rx.text("SPECIALIST AGENT", class_name="eyebrow"), rx.text(State.selected_agent, class_name="advisor-title"), rx.text(State.agent_description, class_name="muted"), spacing="2", align="start"), spacing="5", align="center", class_name="agent-heading"),
                rx.box(
                    rx.text("Ask this agent something specific", class_name="section-title"),
                    rx.text("You can leave this blank for the standard analysis, or add the question you want answered in your final report.", class_name="muted small"),
                    rx.text_area(value=State.agent_question, placeholder=State.agent_placeholder, on_change=lambda value: State.update_field("agent_question", value), class_name="text-area question-area"),
                    rx.hstack(rx.button("Run this agent", on_click=State.ask_agent, class_name="primary-button"), rx.text("Uses your Tier " + State.tier + " context", class_name="agent-context"), spacing="4", align="center"),
                    rx.cond(State.agent_reply != "", rx.box(rx.text("AGENT FINDING", class_name="response-label"), rx.text(State.agent_reply, class_name="agent-summary"), rx.vstack(rx.foreach(State.agent_bullets, lambda bullet: rx.hstack(rx.text("✦", class_name="bullet-star"), rx.text(bullet, class_name="bullet-text"), align="start", spacing="3")), spacing="3", margin_top="18px"), class_name="response-box"), rx.fragment()),
                    spacing="5", width="100%",
                    class_name="content-card advisor-card agent-card",
                ),
                rx.box(rx.hstack(rx.vstack(rx.text("Ready for the next lens?", class_name="section-title"), rx.text("Every completed agent becomes a section in the final family-ready report.", class_name="muted small"), spacing="1", align="start"), rx.button(rx.cond(State.agent_index == 6, "View my full report  →", "Next agent  →"), on_click=State.next_agent, class_name="primary-button"), justify="between", align="center", width="100%"), class_name="submit-panel"),
                spacing="5", padding_y="42px", width="100%",
            ),
        ), class_name="page",
    )


def report_item(item: dict[str, str]) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(item["number"], class_name="report-number"),
            rx.vstack(rx.text(item["name"], class_name="report-agent-name"), rx.text(item["summary"], class_name="muted small"), rx.text(item["details"], white_space="pre-wrap", class_name="report-details"), spacing="1", align="start"),
            spacing="3", align="start",
        ),
        class_name="report-item",
    )


def report_page() -> rx.Component:
    return rx.box(
        navbar("Your study abroad report", "COMPLETE"),
        rx.container(
            rx.vstack(
                rx.box(rx.text("Your complete application story.", class_name="page-title"), rx.text("A shareable summary of your eligibility, matched universities and next actions — designed to make the family conversation easier.", class_name="muted intro-copy"), class_name="intro"),
                rx.box(
                    rx.box("✓", class_name="report-seal"),
                    rx.text("STUDYPATH ELIGIBILITY REPORT", class_name="eyebrow"),
                    rx.text(State.full_name, class_name="report-name"),
                    rx.text(State.degree + " · " + State.field + " · " + State.intake, class_name="muted"),
                    rx.hstack(
                        rx.box(rx.text(State.tier, class_name="report-tier"), rx.text("profile tier", class_name="fine-print"), class_name="report-metric"),
                        rx.box(rx.text(State.score.to_string() + "/100", class_name="report-tier"), rx.text("readiness score", class_name="fine-print"), class_name="report-metric"),
                        rx.box(rx.text("3", class_name="report-tier"), rx.text("university matches", class_name="fine-print"), class_name="report-metric"),
                        spacing="4", wrap="wrap", margin_top="28px",
                    ),
                    class_name="report-hero",
                ),
                rx.box(rx.text("Recommended university route", class_name="section-title"), rx.vstack(rx.foreach(State.recommendations, university_card), spacing="3", margin_top="20px"), class_name="content-card"),
                rx.box(rx.text("Your seven-agent plan", class_name="section-title"), rx.text("The completed counselling insights below are included in your downloadable report.", class_name="muted small"), rx.vstack(rx.foreach(State.agent_summaries, report_item), spacing="3", margin_top="20px"), class_name="content-card"),
                rx.box(rx.hstack(rx.vstack(rx.text("Keep this plan close", class_name="section-title"), rx.text("Download and share the report with your parents, counsellor or sponsor.", class_name="muted small"), spacing="1", align="start"), rx.button("Download my report  ↓", on_click=State.download_report, class_name="primary-button"), justify="between", align="center", width="100%"), class_name="submit-panel"),
                spacing="5", padding_y="48px", width="100%",
            ),
        ), class_name="page",
    )


def index() -> rx.Component:
    return rx.cond(State.screen == "auth", auth_page(), rx.cond(State.screen == "profile", profile_page(), rx.cond(State.screen == "pipeline", pipeline_page(), rx.cond(State.screen == "tier", tier_page(), rx.cond(State.screen == "advisor", advisor_page(), report_page())))))


app = rx.App(
    stylesheets=["/styles.css"],
    theme=rx.theme(appearance="dark", accent_color="cyan", gray_color="slate", radius="large"),
)
app.add_page(index, route="/", title="StudyPath | Study abroad counselling")
