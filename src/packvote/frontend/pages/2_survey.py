import streamlit as st
import os
import httpx
import json

st.set_page_config(page_title="Trip Survey", page_icon="📝")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Load destinations directly from seeds (simulating an endpoint)
SEEDS_PATH = os.path.join(os.path.dirname(__file__), "../../../../seeds/destinations.json")
try:
    with open(SEEDS_PATH, "r") as f:
        DESTINATIONS = json.load(f)
except Exception as e:
    st.error(f"Failed to load destinations: {e}")
    st.stop()

def init_state():
    if "card_idx" not in st.session_state:
        st.session_state.card_idx = 0
    if "swipes" not in st.session_state:
        st.session_state.swipes = []

init_state()

st.title("Trip Survey")

token = st.query_params.get("token")
if not token:
    st.error("Missing participant token in URL! Make sure you used the link provided by your organiser.")
    st.stop()

# If we haven't swiped on all destinations yet
if st.session_state.card_idx < len(DESTINATIONS):
    current_dest = DESTINATIONS[st.session_state.card_idx]
    
    # Modern card-like UI using a container
    with st.container(border=True):
        st.subheader(f"📍 {current_dest['name']}")
        
        # Display vibe tags as markdown badges
        vibes_md = " ".join([f"`{v}`" for v in current_dest.get('vibe_tags', [])])
        st.markdown(f"**Vibes:** {vibes_md}")
        
        # Display best months
        months_md = ", ".join(current_dest.get('best_months', []))
        st.markdown(f"**Best Time to Visit:** {months_md}")
        
        # Display activities
        activities_md = ", ".join(current_dest.get('activities', []))
        st.markdown(f"**Top Activities:** {activities_md}")
        
        # Display rough budget estimate based on seed data
        st.markdown(f"**Est. Budget per person:** ₹{current_dest.get('budget_low', 0):,} - ₹{current_dest.get('budget_high', 0):,}")
        
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👎 Dislike", key=f"dislike_{st.session_state.card_idx}", use_container_width=True):
            st.session_state.swipes.append({"destination": current_dest["name"], "liked": False})
            st.session_state.card_idx += 1
            st.rerun()
    with col2:
        if st.button("👍 Like", key=f"like_{st.session_state.card_idx}", type="primary", use_container_width=True):
            st.session_state.swipes.append({"destination": current_dest["name"], "liked": True})
            st.session_state.card_idx += 1
            st.rerun()

    # Progress bar
    progress = st.session_state.card_idx / len(DESTINATIONS)
    st.progress(progress, text=f"Destination {st.session_state.card_idx + 1} of {len(DESTINATIONS)}")

else:
    st.success("You've swiped through all destinations!")
    
    st.write("### Trip Details")
    budget_max = st.slider("Maximum Budget (₹)", min_value=5000, max_value=100000, step=1000, value=25000)
    
    # Date picker for unavailable dates
    unavailable_dates_str = st.text_input("Unavailable Dates (comma separated, e.g., 'Dec 25, Jan 1')")
    
    if st.button("Submit Survey", type="primary", use_container_width=True):
        dates_list = [d.strip() for d in unavailable_dates_str.split(",") if d.strip()]
        
        payload = {
            "participant_token": token,
            "swipes": st.session_state.swipes,
            "budget_max": budget_max,
            "unavailable_dates": dates_list
        }
        
        with st.spinner("Submitting your responses..."):
            try:
                resp = httpx.post(f"{BACKEND_URL}/responses", json=payload, timeout=10.0)
                if resp.status_code == 200:
                    st.success("Survey submitted successfully! Waiting for other participants to respond.")
                    st.balloons()
                else:
                    st.error(f"Error submitting survey: {resp.text}")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")
