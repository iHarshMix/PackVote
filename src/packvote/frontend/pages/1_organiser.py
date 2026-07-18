import streamlit as st
import httpx
import os

st.set_page_config(page_title="Create a Trip", page_icon="🆕", layout="centered")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Custom header styling
st.markdown("""
<style>
    .header-style {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF8F00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-style">🆕 Create a New Trip</div>', unsafe_allow_html=True)
st.write("Fill in the details below to initialize your group travel decision.")

with st.form("create_trip_form"):
    trip_name = st.text_input("Trip Name", placeholder="e.g. Goa Reunion, Winter Trek...")
    organiser_email = st.text_input("Organiser Email", placeholder="e.g. you@example.com (used for recovery link)")
    dates_rough = st.text_input("Rough Dates", placeholder="e.g. December 2026, Next Summer...")
    
    # Participant count including the organiser
    participant_count = st.number_input(
        "Total Number of Participants (including yourself)", 
        min_value=2, 
        max_value=20, 
        value=3, 
        step=1
    )
    
    submit_button = st.form_submit_button("Initialize Trip", type="primary", use_container_width=True)

if submit_button:
    if not trip_name or not organiser_email or not dates_rough:
        st.error("Please fill in all the form fields.")
    else:
        with st.spinner("Creating trip..."):
            try:
                # 1. Create the trip
                trip_payload = {
                    "name": trip_name,
                    "dates_rough": dates_rough,
                    "participant_count": int(participant_count),
                    "organiser_email": organiser_email
                }
                
                resp = httpx.post(f"{BACKEND_URL}/trips", json=trip_payload, timeout=10.0)
                if resp.status_code != 201:
                    st.error(f"Failed to create trip: {resp.text}")
                    st.stop()
                    
                trip_data = resp.json()
                trip_id = trip_data["id"]
                management_token = trip_data["management_token"]
                
                # 2. Add participants (subtracting 1 for the organiser who is created automatically)
                participants_to_create = int(participant_count) - 1
                if participants_to_create > 0:
                    part_resp = httpx.post(
                        f"{BACKEND_URL}/trips/{trip_id}/participants", 
                        json={"count": participants_to_create},
                        timeout=10.0
                    )
                    if part_resp.status_code != 200:
                        st.error(f"Failed to add participants: {part_resp.text}")
                        st.stop()
                
                # 3. Transition trip to survey phase
                survey_resp = httpx.post(f"{BACKEND_URL}/trips/{trip_id}/start-survey", timeout=10.0)
                if survey_resp.status_code != 200:
                    st.error(f"Failed to start survey phase: {survey_resp.text}")
                    st.stop()
                
                # Success! Set query params and redirect to management dashboard
                st.success("Trip successfully initialized and started!")
                st.query_params["token"] = management_token
                st.switch_page("pages/6_manage.py")
                
            except Exception as e:
                st.error(f"An error occurred while communicating with the backend: {e}")
