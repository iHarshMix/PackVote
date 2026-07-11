import streamlit as st
import os
import httpx

st.set_page_config(page_title="Recover Trip Links", page_icon="📧", layout="centered")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("📧 Recover Organiser Link")
st.write("Forgot or lost your management link? Enter your email below to have the trip management links sent back to you.")

email = st.text_input("Organiser Email Address", placeholder="organiser@example.com")

if st.button("Send Recovery Email", type="primary", use_container_width=True):
    if not email.strip():
        st.error("Please enter a valid email address.")
    else:
        with st.spinner("Processing recovery request..."):
            try:
                resp = httpx.post(f"{BACKEND_URL}/trips/recover", json={"email": email.strip()}, timeout=10.0)
                if resp.status_code == 200:
                    st.success(
                        "If that email address has any active trips associated with it, "
                        "we've sent the recovery links to it. Please check your inbox (and spam folder)!"
                    )
                else:
                    st.error(f"Error requesting recovery: {resp.text}")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")
