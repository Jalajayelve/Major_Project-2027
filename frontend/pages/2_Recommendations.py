import streamlit as st

from utils.api_client import match_universities

st.title("Recommendations")

with st.form("recommendation_form"):
    gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.01, value=3.5)
    tier = st.selectbox("Target tier", ["low", "medium", "high", "elite"])
    country = st.selectbox("Preferred country", ["USA", "Canada", "UK", "Australia", "All"])
    submitted = st.form_submit_button("Find matches")

if submitted:
    payload = {
        "gpa": gpa,
        "tier": tier,
        "country": country,
    }
    try:
        result = match_universities(payload)
        st.json(result)
        if result.get("matched_universities"):
            st.subheader("Matched universities")
            for university in result["matched_universities"]:
                st.markdown(f"- **{university['name']}** — {university['country']} ({university['tier']})")
        else:
            st.warning("No universities matched your filter. Try adjusting GPA or tier.")
    except Exception as exc:
        st.error(f"Unable to fetch recommendations: {exc}")
