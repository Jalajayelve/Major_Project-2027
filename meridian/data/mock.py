"""Structured mock data for the whole journey.

Everything the UI shows comes from here (or, later, from the backend through
`meridian.services`). All figures are ILLUSTRATIVE placeholders, not real
admissions data.
"""
from __future__ import annotations

from typing import Any

# ── Profile form schema + defaults ─────────────────────────────────────────
STUDENT_PROFILE: dict[str, str] = {
    # personal
    "full_name": "Aarav Mehta",
    "email": "aarav.mehta@example.com",
    "phone": "+91 98200 00000",
    "dob": "2001-04-18",
    "nationality": "Indian",
    "city": "Thane, Maharashtra",
    # academic
    "university": "University of Mumbai",
    "degree": "B.E. Computer Engineering",
    "gpa": "8.4",
    "gpa_scale": "10",
    "grad_year": "2023",
    "backlogs": "0",
    # tests
    "gre_verbal": "158",
    "gre_quant": "165",
    "gre_awa": "4.0",
    "toefl": "108",
    "ielts": "",
    "gmat": "",
    # experience
    "work_years": "2",
    "employer": "Infosys",
    "role": "Software Engineer",
    "internships": "2",
    "research": "1 conference paper, 1 ongoing project",
    "projects": "Built a demand-forecasting service used by 3 internal teams. Open-source contributor to a data-validation library.",
    # goals
    "degree_goal": "MS",
    "field": "Computer Science",
    "career_goal": "Machine learning engineer at a product company, later leading an applied research team.",
    "budget": "60000",
    "funding": "Savings + education loan",
    # intake
    "intake": "Fall 2027",
    "apply_by": "December 2026",
    "start_prep": "Already started",
    # preferred programs
    "programs": "MS Computer Science, MS Data Science, MS Artificial Intelligence",
    "regions": "California, Texas, Northeast",
    "class_size": "Mid-size",
}

_F = lambda key, label, kind="text", placeholder="", options=None, wide=False: {  # noqa: E731
    "key": key, "label": label, "kind": kind, "placeholder": placeholder,
    "options": options or [], "wide": wide,
}

FORM_SCHEMA: list[dict[str, Any]] = [
    {"id": "personal", "label": "Personal", "fields": [
        _F("full_name", "Full name", placeholder="As on passport"),
        _F("email", "Email", "email", "name@example.com"),
        _F("phone", "Phone", placeholder="+91 …"),
        _F("dob", "Date of birth", "date"),
        _F("nationality", "Nationality"),
        _F("city", "Current city"),
    ]},
    {"id": "academic", "label": "Academic", "fields": [
        _F("university", "Undergraduate university"),
        _F("degree", "Degree and major"),
        _F("gpa", "GPA / percentage"),
        _F("gpa_scale", "Scale", "select", options=["4", "10", "100"]),
        _F("grad_year", "Graduation year"),
        _F("backlogs", "Active backlogs"),
    ]},
    {"id": "tests", "label": "Test scores", "fields": [
        _F("gre_verbal", "GRE verbal (130–170)"),
        _F("gre_quant", "GRE quant (130–170)"),
        _F("gre_awa", "GRE writing (0–6)"),
        _F("toefl", "TOEFL (0–120)"),
        _F("ielts", "IELTS (0–9)", placeholder="Leave empty if not taken"),
        _F("gmat", "GMAT (200–800)", placeholder="MBA applicants"),
    ]},
    {"id": "experience", "label": "Experience", "fields": [
        _F("work_years", "Years of work experience"),
        _F("employer", "Current or last employer"),
        _F("role", "Role"),
        _F("internships", "Internships completed"),
        _F("research", "Research and publications", wide=True),
        _F("projects", "Projects and leadership", "textarea", "Two or three lines is enough", wide=True),
    ]},
    {"id": "goals", "label": "Study goals", "fields": [
        _F("degree_goal", "Degree", "select", options=["MS", "MBA"]),
        _F("field", "Field of study"),
        _F("budget", "Total budget (USD)"),
        _F("funding", "Funding plan"),
        _F("career_goal", "Career goal", "textarea", "Where do you want this degree to take you?", wide=True),
    ]},
    {"id": "intake", "label": "Target intake", "fields": [
        _F("intake", "Target intake", "select", options=["Spring 2027", "Fall 2027", "Spring 2028", "Fall 2028"]),
        _F("apply_by", "Planning to apply by"),
        _F("start_prep", "Preparation status", "select", options=["Just exploring", "Already started", "Ready to submit"]),
    ]},
    {"id": "programs", "label": "Preferred programs", "fields": [
        _F("programs", "Programs of interest", "textarea", "Separate with commas", wide=True),
        _F("regions", "Preferred regions"),
        _F("class_size", "Campus size", "select", options=["Small", "Mid-size", "Large", "No preference"]),
    ]},
]

# ── Documents ───────────────────────────────────────────────────────────────
DOC_SLOTS: list[dict[str, str]] = [
    {"slot": "resume", "label": "Resume / CV", "hint": "PDF or DOCX, up to two pages"},
    {"slot": "transcript", "label": "Transcript", "hint": "Official or self-attested marksheets"},
    {"slot": "sop", "label": "Statement of purpose", "hint": "Draft is fine — agents read for fit"},
    {"slot": "lor", "label": "Letters of recommendation", "hint": "One file, or the strongest letter"},
    {"slot": "other", "label": "Other documents", "hint": "Certificates, publications, portfolios"},
]

SAMPLE_DOCS: dict[str, dict[str, str]] = {
    "resume": {"name": "Aarav_Mehta_Resume.pdf", "size": "148 KB"},
    "transcript": {"name": "BE_Transcript_Sem1-8.pdf", "size": "612 KB"},
    "sop": {"name": "SOP_draft_v3.docx", "size": "36 KB"},
    "lor": {"name": "LOR_Prof_Kulkarni.pdf", "size": "94 KB"},
    "other": {"name": "ICML_workshop_paper.pdf", "size": "1.1 MB"},
}

# ── Agents + event contract ─────────────────────────────────────────────────
AGENTS: list[dict[str, Any]] = [
    {"id": "profile", "no": "01", "name": "Profile", "desc": "Reads your academics, scores and experience into one profile.", "status": "waiting", "progress": 0, "pct": "0%"},
    {"id": "university", "no": "02", "name": "University", "desc": "Matches you against US universities by fit and selectivity.", "status": "waiting", "progress": 0, "pct": "0%"},
    {"id": "program", "no": "03", "name": "Program", "desc": "Compares curricula, faculty focus and outcomes for your field.", "status": "waiting", "progress": 0, "pct": "0%"},
    {"id": "financial", "no": "04", "name": "Financial", "desc": "Estimates tuition, living costs and your funding gap.", "status": "waiting", "progress": 0, "pct": "0%"},
    {"id": "scholarship", "no": "05", "name": "Scholarship", "desc": "Finds awards and assistantships you are eligible for.", "status": "waiting", "progress": 0, "pct": "0%"},
    {"id": "career", "no": "06", "name": "Career", "desc": "Maps target roles, employers and expected outcomes.", "status": "waiting", "progress": 0, "pct": "0%"},
    {"id": "extracurricular", "no": "07", "name": "Extracurricular", "desc": "Weighs research, projects and leadership beyond grades.", "status": "waiting", "progress": 0, "pct": "0%"},
]

AGENT_IDS = [a["id"] for a in AGENTS]

# Event types the UI can consume from the backend (WebSocket) later.
EVENT_TYPES = [f"{a}_{phase}" for a in AGENT_IDS for phase in ("processing", "completed")]

# ── Universities (map projection: lon -125..-66, lat 24..50) ────────────────
LON_MIN, LON_MAX, LAT_MIN, LAT_MAX = -125.0, -66.0, 24.0, 50.0


def project(lon: float, lat: float) -> tuple[float, float]:
    """Return (x%, y%) inside the map frame."""
    return (lon - LON_MIN) / (LON_MAX - LON_MIN) * 100, (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * 100


def _uni(id_, name, short, city, lon, lat, tier, prob, tuition, program, note, deadline):
    x, y = project(lon, lat)
    return {
        "id": id_, "name": name, "short": short, "city": city, "lon": lon, "lat": lat,
        "x": f"{x:.2f}%", "y": f"{y:.2f}%", "xf": x, "yf": y,
        "tier": tier, "prob": prob, "prob_str": f"{prob}%", "tuition": tuition,
        "tuition_str": f"${tuition:,}", "program": program, "note": note, "deadline": deadline,
    }


UNIVERSITIES: list[dict[str, Any]] = [
    _uni("cmu", "Carnegie Mellon University", "CMU", "Pittsburgh, PA", -79.94, 40.44, "Ambitious", 22, 58000,
         "MS Machine Learning", "Strong research alignment with your forecasting work.", "12 Dec 2026"),
    _uni("ut", "University of Texas at Austin", "UT Austin", "Austin, TX", -97.73, 30.28, "Target", 46, 38000,
         "MS Computer Science", "Large program with industry ties and lower total cost.", "15 Dec 2026"),
    _uni("gt", "Georgia Institute of Technology", "Georgia Tech", "Atlanta, GA", -84.40, 33.78, "Target", 51, 34000,
         "MS Computer Science (ML)", "Balanced fit; scores sit near the admitted median.", "1 Dec 2026"),
    _uni("ucsd", "University of California, San Diego", "UC San Diego", "San Diego, CA", -117.24, 32.88, "Target", 41, 44000,
         "MS Data Science", "Good match for applied data work and West-coast placements.", "5 Jan 2027"),
    _uni("neu", "Northeastern University", "Northeastern", "Boston, MA", -71.09, 42.34, "Safe", 72, 56000,
         "MS Artificial Intelligence", "Co-op model lifts your experience profile.", "15 Jan 2027"),
    _uni("asu", "Arizona State University", "Arizona State", "Tempe, AZ", -111.93, 33.42, "Safe", 84, 36000,
         "MS Computer Science", "High admit likelihood, strong scholarship options.", "1 Mar 2027"),
]

# ── Results ─────────────────────────────────────────────────────────────────
PROFILE_STRENGTH: dict[str, Any] = {
    "score": 78,
    "label": "Strong",
    "dimensions": [
        {"name": "Academics", "score": 82, "pct": "82%"},
        {"name": "Test scores", "score": 86, "pct": "86%"},
        {"name": "Work experience", "score": 74, "pct": "74%"},
        {"name": "Research", "score": 61, "pct": "61%"},
        {"name": "Statement of purpose", "score": 70, "pct": "70%"},
    ],
}

PROGRAMS: list[dict[str, str]] = [
    {"university": "Georgia Tech", "program": "MS Computer Science (ML)", "match": "88%", "duration": "2 years", "focus": "Machine learning, systems"},
    {"university": "UT Austin", "program": "MS Computer Science", "match": "84%", "duration": "2 years", "focus": "AI, data systems"},
    {"university": "UC San Diego", "program": "MS Data Science", "match": "81%", "duration": "1.5 years", "focus": "Applied statistics, ML"},
    {"university": "Northeastern", "program": "MS Artificial Intelligence", "match": "79%", "duration": "2 years + co-op", "focus": "Applied AI, industry co-op"},
    {"university": "CMU", "program": "MS Machine Learning", "match": "74%", "duration": "1.5 years", "focus": "Research-heavy ML"},
]

FINANCIAL: dict[str, Any] = {
    "total": 61200,
    "total_str": "$61,200",
    "period": "Per year, blended across your shortlist",
    "budget_str": "$60,000",
    "gap_str": "$1,200 over budget",
    "items": [
        {"name": "Tuition", "amount": "$38,000", "share": 62, "w": "62%"},
        {"name": "Living", "amount": "$16,800", "share": 27, "w": "27%"},
        {"name": "Health insurance", "amount": "$3,000", "share": 5, "w": "5%"},
        {"name": "Travel and visa", "amount": "$1,800", "share": 3, "w": "3%"},
        {"name": "Books and misc.", "amount": "$1,600", "share": 3, "w": "3%"},
    ],
}

SCHOLARSHIPS: list[dict[str, str]] = [
    {"name": "Merit award, Arizona State", "value": "Up to $10,000", "fit": "High", "type": "Merit"},
    {"name": "Graduate assistantship, UT Austin", "value": "Tuition offset + stipend", "fit": "Medium", "type": "Assistantship"},
    {"name": "Fulbright-Nehru Master's Fellowship", "value": "Full funding", "fit": "Low", "type": "External"},
    {"name": "Northeastern Global Scholars", "value": "Up to $15,000", "fit": "Medium", "type": "Merit"},
]

CAREER: dict[str, Any] = {
    "summary": "Your background lines up well with applied machine-learning roles.",
    "roles": [
        {"role": "Machine Learning Engineer", "fit": 88, "w": "88%", "salary": "$135k–165k"},
        {"role": "Data Scientist", "fit": 82, "w": "82%", "salary": "$120k–150k"},
        {"role": "Software Engineer, ML platform", "fit": 79, "w": "79%", "salary": "$130k–160k"},
        {"role": "Applied Research Engineer", "fit": 58, "w": "58%", "salary": "$140k–180k"},
    ],
}

EXTRACURRICULAR: dict[str, Any] = {
    "score": 64,
    "items": [
        {"name": "Research output", "score": 61, "w": "61%"},
        {"name": "Open-source and projects", "score": 78, "w": "78%"},
        {"name": "Leadership", "score": 52, "w": "52%"},
        {"name": "Community and volunteering", "score": 45, "w": "45%"},
    ],
}

KEY_FACTORS: list[dict[str, Any]] = [
    {"name": "GRE quantitative score", "impact": "+9", "positive": True, "w": "90%"},
    {"name": "Two years of relevant work experience", "impact": "+7", "positive": True, "w": "70%"},
    {"name": "Undergraduate GPA", "impact": "+6", "positive": True, "w": "60%"},
    {"name": "Publication in progress", "impact": "+4", "positive": True, "w": "40%"},
    {"name": "Limited leadership evidence", "impact": "−4", "positive": False, "w": "40%"},
    {"name": "Statement of purpose still in draft", "impact": "−3", "positive": False, "w": "30%"},
]

# Continental US outline as (lon, lat) for the map backdrop.
US_OUTLINE: list[tuple[float, float]] = [
    (-124.7, 48.4), (-122.8, 49.0), (-95.2, 49.0), (-94.6, 48.7), (-92.0, 48.3), (-89.6, 48.0), (-84.8, 46.9),
    (-82.5, 45.3), (-82.4, 43.0), (-83.1, 42.0), (-79.0, 42.8), (-76.5, 43.6), (-75.0, 45.0), (-71.5, 45.0),
    (-70.2, 46.5), (-69.2, 47.4), (-67.8, 47.0), (-67.0, 44.8), (-70.2, 43.6), (-70.8, 42.7), (-70.0, 41.8),
    (-71.5, 41.3), (-74.0, 40.6), (-74.0, 39.4), (-75.5, 38.4), (-76.0, 37.0), (-75.6, 35.3), (-77.0, 34.5),
    (-79.0, 33.3), (-81.0, 31.9), (-81.3, 30.0), (-80.0, 27.0), (-80.3, 25.2), (-81.2, 25.3), (-82.8, 27.8),
    (-82.7, 29.2), (-84.0, 30.0), (-86.0, 30.3), (-88.5, 30.3), (-89.5, 30.2), (-89.2, 29.0), (-91.0, 29.2),
    (-93.8, 29.7), (-95.0, 29.0), (-97.2, 27.6), (-97.4, 25.9), (-99.1, 26.4), (-100.6, 28.6), (-101.5, 29.8),
    (-103.0, 29.0), (-104.5, 29.7), (-106.5, 31.8), (-108.2, 31.8), (-108.2, 31.3), (-111.0, 31.3),
    (-114.8, 32.5), (-117.1, 32.5), (-118.5, 34.0), (-120.6, 34.6), (-122.4, 37.2), (-123.8, 39.5),
    (-124.4, 42.0), (-124.1, 44.0), (-124.0, 46.2),
]

# ── Landing content ─────────────────────────────────────────────────────────
STEPS: list[dict[str, str]] = [
    {"no": "01", "title": "Complete your profile", "text": "Seven short sections: academics, scores, experience, goals, intake and the programs you already have in mind."},
    {"no": "02", "title": "Hand over your documents", "text": "Resume, transcript, statement of purpose and letters. Drafts are welcome."},
    {"no": "03", "title": "Seven agents investigate", "text": "Each one studies a different part of your application and reports back as it finishes."},
    {"no": "04", "title": "Receive your dossier", "text": "A personal report with matches, probabilities, costs and next steps, ready to download."},
]

SCENE = {
    "date": "SEP 2026",
    "destination": "USA",
    "program": "MS / MBA",
    "application_no": "MRD-27-0418",
    "status": "IN PREPARATION",
    "shortlist": "CMU · UT Austin · Georgia Tech",
}


def build_report(profile: dict[str, str] | None = None) -> dict[str, Any]:
    """Assemble the final report object (the shape the backend will return)."""
    p = {**STUDENT_PROFILE, **(profile or {})}
    return {
        "student": {
            "name": p["full_name"], "target": "United States", "program": f"{p['degree_goal']} {p['field']}",
            "intake": p["intake"], "report_no": "MRD-27-0418",
        },
        "profile_strength": PROFILE_STRENGTH,
        "universities": UNIVERSITIES,
        "programs": PROGRAMS,
        "financial": FINANCIAL,
        "scholarships": SCHOLARSHIPS,
        "career": CAREER,
        "extracurricular": EXTRACURRICULAR,
        "key_factors": KEY_FACTORS,
    }
