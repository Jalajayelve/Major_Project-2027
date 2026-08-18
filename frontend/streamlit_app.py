import streamlit as st


st.set_page_config(page_title="Study Abroad AI", page_icon="🎓", layout="wide")

st.title("Study Abroad AI")
st.write("Explore your study-abroad fit, compare likely targets, and understand your recommendations.")

st.markdown(
    """
    ### Start here
    - Go to the Profile Form page to enter your student profile.
    - Review your recommendations on the Recommendations page.
    - Learn more about the platform on the About page.
    """
)

st.info("The frontend is configured to call the Flask backend at http://localhost:5000.")
