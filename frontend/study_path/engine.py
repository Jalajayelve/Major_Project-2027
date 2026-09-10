"""Development recommendation engine for the StudyPath Reflex experience.

The public functions here deliberately return plain dictionaries/lists so a live
LangGraph gateway can replace them without changing the Reflex screens.
"""

from __future__ import annotations


def _number(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return default


def profile_score(profile: dict[str, str]) -> tuple[int, str, str]:
    """Return a transparent readiness score, tier, and explanation."""
    gpa = _number(profile.get("gpa", ""))
    english = _number(profile.get("english_score", ""))
    experience = _number(profile.get("experience_years", ""))
    score = min(46, round(gpa / 10 * 46))
    score += min(24, round(english / 9 * 24))
    score += min(15, round(experience * 3))
    score += 10 if profile.get("sop", "").strip() else 0
    score += 5 if profile.get("activities", "").strip() else 0
    score = max(0, min(score, 100))

    if score >= 78:
        return score, "Tier 1", "Ambitious match profile — apply across reach and target universities."
    if score >= 58:
        return score, "Tier 2", "Competitive profile — balance target options with a few ambitious choices."
    return score, "Tier 3", "Developing profile — build a strong, realistic shortlist and improve key signals."


def universities_for(profile: dict[str, str], tier: str) -> list[dict[str, str]]:
    country = profile.get("country", "Global") or "Global"
    field = profile.get("field", "your chosen field") or "your chosen field"
    choices = {
        "Tier 1": [
            ("University of Southern California", "United States", "Reach", "82%"),
            ("Northeastern University", "United States", "Target", "76%"),
            ("University of Illinois Urbana-Champaign", "United States", "Target", "73%"),
        ],
        "Tier 2": [
            ("Arizona State University", "United States", "Target", "79%"),
            ("University at Buffalo, SUNY", "United States", "Target", "74%"),
            ("Illinois Institute of Technology", "United States", "Safe", "81%"),
        ],
        "Tier 3": [
            ("University of Texas at Arlington", "United States", "Target", "78%"),
            ("George Mason University", "United States", "Safe", "84%"),
            ("University of New Haven", "United States", "Target", "76%"),
        ],
    }
    return [
        {
            "name": name,
            "country": location,
            "category": category,
            "chance": chance,
            "program": field,
            "note": f"A {category.lower()} fit for a student applying from {country}.",
        }
        for name, location, category, chance in choices[tier]
    ]


AGENT_RESPONSES = {
    "Program advisor": "Program Agent: I compare your academic background with course content and specialisations. Your next best action is to shortlist two programmes per university and verify prerequisites.",
    "Cost planner": "Financial Agent: I estimate tuition, living costs and funding gap. Start by setting a yearly budget and selecting countries that fit it before you apply.",
    "Scholarship finder": "Scholarship Agent: I look for awards matching your academic record, nationality and intended field. Prepare your transcript and a reusable achievement list first.",
    "Career guide": "Career Agent: I map programmes to industry or research outcomes. Tell me your ideal role and I will help compare post-study work routes.",
    "Profile coach": "Profile Agent: Your strongest application levers are academic evidence, a focused SOP and meaningful activities. I can help turn these into an action plan.",
}


def agent_answer(agent: str, question: str, tier: str) -> str:
    base = AGENT_RESPONSES.get(agent, "Counselling Agent: I can help you plan the next application step.")
    if question.strip():
        return f"{base}\n\nFor your {tier} profile, on your question — “{question.strip()}” — I recommend prioritising evidence you can verify, then reviewing deadlines before committing."
    return base


def agent_result(agent: str, question: str, profile: dict[str, str], tier: str) -> dict[str, object]:
    """Structured stand-in for one of the seven LangGraph agent responses."""
    field = profile.get("field", "your intended field") or "your intended field"
    degree = profile.get("degree", "Masters") or "Masters"
    budget = profile.get("budget", "your stated budget") or "your stated budget"
    goal = profile.get("career_goal", "your long-term goal") or "your long-term goal"
    results: dict[str, tuple[str, list[str]]] = {
        "Profile Compass": (f"Your {tier} profile is ready for matching.", ["Academic, English-language and experience signals are in your shared student context.", "Your SOP, activities and research evidence are the strongest application levers to improve next.", "Keep original transcripts and test-score reports ready for document review."]),
        "University Matcher": (f"Your U.S. university strategy is calibrated for {degree} study in {field}.", ["Use reach, target and safe choices together rather than applying only to one confidence category.", "Admission confidence is an estimate, not a guarantee; verify current requirements before paying fees.", "Confirm each university’s U.S. intake dates and English-score rules early."]),
        "Program Architect": (f"Programme fit analysis is focused on {field}.", ["Shortlist two programmes per university: one specialist choice and one flexible alternative.", "Compare prerequisite modules against your previous degree before finalising choices.", "Check capstone, internship and thesis options against your long-term goal."]),
        "Finance Planner": (f"Your U.S. planning baseline uses {budget} per year.", ["Build a state-by-state view of tuition, housing, insurance and visa costs.", "Reserve funds for deposits, travel and exchange-rate movement.", "Keep proof-of-funds requirements separate from university tuition estimates."]),
        "Scholarship Finder": ("Three funding routes are worth preparing for.", ["Merit scholarship — estimated 20–40% tuition coverage; support it with GPA, leadership and SOP evidence.", "University international award — check programme-specific deadlines before your main application.", "External grant route — prepare a one-page achievements list and two recommender contacts."]),
        "Career Navigator": (f"Career planning is aligned to {goal}.", ["Compare graduate employment reports and U.S. post-study work routes for each university.", "Prioritise programmes with co-op, internship or employer-project opportunities.", "Turn your target role into three measurable skills to demonstrate before graduation."]),
        "Documents Coach": ("Your application document checklist is organised.", ["Core set: passport, transcripts, test scores, CV, SOP and letters of recommendation.", "SOP review: lead with motivation, connect evidence to the programme, then finish with a credible goal.", "Add evidence for leadership, research, volunteering, competitions or publications where available."]),
    }
    summary, bullets = results[agent]
    if question.strip():
        bullets = [*bullets, f"Your question noted: “{question.strip()}”. Keep it as an action item for your counsellor."]
    return {"summary": summary, "bullets": bullets}
