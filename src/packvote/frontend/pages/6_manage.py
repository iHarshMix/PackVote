import streamlit as st
import os
import httpx

st.set_page_config(page_title="Trip Management", page_icon="⚙️", layout="centered")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("⚙️ Trip Management")
st.write("Welcome to your trip organizer dashboard! Bookmark this page or keep the link safe.")

# Retrieve management token from URL query params
token = st.query_params.get("token")
if not token:
    st.error("Missing management token! Organisers must access this page via the management link.")
    st.info("💡 If you lost your link, use the recovery page to have it emailed to you.")
    st.stop()

# Fetch trip management data from backend
with st.spinner("Fetching trip dashboard..."):
    try:
        resp = httpx.get(f"{BACKEND_URL}/trips/manage/{token}", timeout=10.0)
        if resp.status_code == 200:
            trip_data = resp.json()
        elif resp.status_code == 404:
            st.error("Invalid management token! Trip not found.")
            st.stop()
        else:
            st.error(f"Error fetching trip: {resp.text}")
            st.stop()
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
        st.stop()

trip_id = trip_data["id"]
trip_name = trip_data["name"]
trip_status = trip_data["status"]
participants = trip_data["participants"]

# Display Trip Details
st.markdown(f"### Trip: **{trip_name}**")
st.write(f"**Trip ID:** `{trip_id}`")

# Render status with custom badge representation
status_colors = {
    "setup": "🔵 Setup",
    "survey": "🟢 Survey Active",
    "reveal": "🟡 Preference Reveal",
    "voting": "🟠 Voting Active",
    "complete": "🟣 Completed"
}
display_status = status_colors.get(trip_status, trip_status.capitalize())
st.write(f"**Current Status:** {display_status}")

st.write("---")

# Section: Share Survey Links
st.subheader("👥 Participant Survey Links")
st.write("Copy and share these links with each participant (e.g., via WhatsApp or Email):")

for p in participants:
    # Highlight the organiser participant specifically
    display_name = f"👤 {p['name']} (Organiser)" if p.get("name") == "Organiser" else f"👤 {p['name']}"
    
    with st.container(border=True):
        st.markdown(f"**{display_name}**")
        st.code(p["survey_url"], language="text")

st.write("---")

# Section: Management Actions
st.subheader("🛠️ Management Actions")

if trip_status == "survey":
    st.info("The survey is active. When all participants have finished swiping, the system will automatically proceed.")
    st.write("If some participants are unresponsive, you can close the survey early using the button below to generate recommendations with the responses received so far.")
    
    if st.button("Force Close Survey & Generate Recs", type="primary", use_container_width=True):
        with st.spinner("Closing survey and starting AI pipeline..."):
            try:
                close_resp = httpx.post(
                    f"{BACKEND_URL}/trips/{trip_id}/force-close",
                    json={"management_token": token},
                    timeout=10.0
                )
                if close_resp.status_code == 200:
                    result = close_resp.json()
                    st.success(f"Survey closed successfully! Received {result['responses_received']} of {result['total_participants']} responses.")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"Failed to close survey: {close_resp.text}")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")
                
elif trip_status == "setup":
    st.warning("This trip is in Setup phase. Participants cannot submit responses yet.")
    
elif trip_status == "reveal":
    st.success("Preferences are ready to be revealed!")
    st.write("Visit the group dashboard to view preferences and start the vote.")
    
else:
    st.write("No actions available for the current phase.")
