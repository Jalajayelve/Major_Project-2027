import streamlit as st

from utils.api_client import match_universities, predict_profile

st.title("Student Profile Form")

program_type = st.selectbox("Program type", ["MS", "MBA"])

if program_type == "MS":
    gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.01, value=3.5)
    gre_score = st.number_input("GRE score", min_value=0.0, max_value=340.0, step=1.0, value=320.0)
    toefl_score = st.number_input("TOEFL score", min_value=0.0, max_value=120.0, step=1.0, value=95.0)
    research_experience = st.slider("Research experience (years)", 0, 5, 2)
    work_experience = st.slider("Work experience (years)", 0, 10, 1)
    payload = {
        "gpa": gpa,
        "gre_score": gre_score,
        "toefl_score": toefl_score,
        "research_experience": research_experience,
        "work_experience": work_experience,
    }
else:
    gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.01, value=3.4)
    gmat_score = st.number_input("GMAT score", min_value=0.0, max_value=800.0, step=1.0, value=680.0)
    work_experience = st.slider("Work experience (years)", 0, 15, 3)
    essay_score = st.number_input("Essay score", min_value=0.0, max_value=10.0, step=0.1, value=7.5)
    payload = {
        "gpa": gpa,
        "gmat_score": gmat_score,
        "work_experience": work_experience,
        "essay_score": essay_score,
    }

if st.button("Submit profile"):
    try:
        result = predict_profile(payload, program_type.lower())
        st.success("Profile submitted successfully.")
        st.json(result)
        match_payload = {
            "gpa": payload.get("gpa", 0),
            "tier": "medium",
            "country": "USA",
        }
        recommendations = match_universities(match_payload)
        st.subheader("Recommended universities")
        st.json(recommendations)
    except Exception as exc:
        st.error(f"There was an error contacting the backend: {exc}")
