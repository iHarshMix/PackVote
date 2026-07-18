import streamlit as st
import os
import httpx
from datetime import datetime

st.set_page_config(page_title="Preference Reveal", page_icon="👁️", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Retrieve trip_id from URL or session state ───────────────────────────────
trip_id = st.query_params.get("trip_id") or st.session_state.get("trip_id")
if not trip_id:
    st.error("Missing Trip ID! Please access this page from the dashboard.")
    st.stop()
else:
    st.session_state["trip_id"] = trip_id
    st.query_params["trip_id"] = trip_id

# Optionally retrieve management token (only organisers have it)
management_token = st.query_params.get("token") or st.session_state.get("token")

# ── Fetch reveal data ────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_reveal(tid):
    resp = httpx.get(f"{BACKEND_URL}/trips/{tid}/reveal", timeout=15.0)
    if resp.status_code == 200:
        return resp.json()
    return None

reveal_data = fetch_reveal(trip_id)
if not reveal_data:
    st.error("Could not load reveal data. The trip may not have reached the reveal phase yet.")
    st.stop()

aggregated = reveal_data["aggregated"]
recommendations = reveal_data["recommendations"]

# ── Page Header ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
.reveal-header {
    text-align: center;
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}
.reveal-sub {
    text-align: center;
    color: #888;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}
.rec-card {
    border: 1px solid #333;
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}
.vibe-tag {
    display: inline-block;
    background: #0f3460;
    color: #e0e0e0;
    padding: 3px 10px;
    border-radius: 12px;
    margin: 2px;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="reveal-header">👁️ Preference Reveal</div>', unsafe_allow_html=True)
st.markdown('<div class="reveal-sub">Here\'s what your group collectively wanted — and what the AI recommends.</div>', unsafe_allow_html=True)

# ── Section 1: Aggregated Preferences ────────────────────────────────────────
st.subheader("📊 Group Preferences")

col1, col2 = st.columns(2)

with col1:
    # Top destinations
    st.markdown("**🏆 Most Swiped-Right Destinations**")
    top_dests = aggregated.get("top_destinations", [])
    if top_dests:
        for i, dest in enumerate(top_dests, 1):
            st.markdown(f"{i}. **{dest}**")
    else:
        st.info("No swipe data available.")

    # Shared vibes
    st.markdown("**🎭 Shared Vibes**")
    vibes = aggregated.get("vibe_overlap", [])
    if vibes:
        vibes_html = " ".join([f'<span class="vibe-tag">{v}</span>' for v in vibes])
        st.markdown(vibes_html, unsafe_allow_html=True)
    else:
        st.info("No shared vibes detected.")

with col2:
    # Budget distribution
    st.markdown("**💰 Budget Distribution**")
    budget_dist = aggregated.get("budget_distribution", [])
    if budget_dist:
        import pandas as pd
        df = pd.DataFrame(budget_dist)
        st.bar_chart(df.set_index("name")["budget_max"])
    sweet_spot = aggregated.get("budget_sweet_spot", "N/A")
    st.metric("Budget Sweet Spot", f"₹{sweet_spot:,}" if isinstance(sweet_spot, int) else sweet_spot)

    # Date conflicts
    st.markdown("**📅 Blocked Dates**")
    conflicts = aggregated.get("date_conflicts", [])
    if conflicts:
        st.warning(", ".join(conflicts))
    else:
        st.success("No date conflicts!")

st.divider()

# ── Section 2: AI Recommendations ────────────────────────────────────────────
st.subheader("💡 AI Travel Recommendations")

for idx, rec in enumerate(recommendations, 1):
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"### #{idx} — {rec['destination']}")
            st.markdown(f"👍 **Why it fits:** {rec['fit_reason']}")
            st.markdown(f"⚖️ **Tradeoff:** {rec['tradeoff']}")
        with c2:
            st.metric("Est. Budget", f"₹{rec['budget_estimate']:,}")

st.divider()

# ── Section 3: Organiser Actions ─────────────────────────────────────────────

# Check current trip status to determine what buttons to show
@st.cache_data(ttl=5)
def fetch_trip_status(tid):
    resp = httpx.get(f"{BACKEND_URL}/trips/{tid}/status", timeout=10.0)
    if resp.status_code == 200:
        return resp.json().get("status")
    return None

current_status = fetch_trip_status(trip_id)

if current_status == "reveal" and management_token:
    st.subheader("🚀 Open Voting Phase")
    st.info("As the organiser, you can now open the voting phase. "
            "All participants will be able to rank the recommended destinations.")

    vote_hours = st.slider("Voting countdown (hours)", min_value=1, max_value=48, value=12)

    if st.button("🗳️ Open Voting Now", type="primary", use_container_width=True):
        with st.spinner("Opening voting phase..."):
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/trips/{trip_id}/open-vote",
                    json={
                        "management_token": management_token,
                        "vote_duration_hours": vote_hours,
                    },
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    st.success("Voting is now open! Redirecting to the ballot page...")
                    st.session_state["trip_id"] = trip_id
                    st.query_params["trip_id"] = trip_id
                    st.cache_data.clear()
                    st.switch_page("pages/5_vote.py")
                else:
                    st.error(f"Error opening vote: {resp.text}")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")

elif current_status == "voting":
    st.info("🗳️ Voting is currently active!")
    if st.button("Go to Voting Page →", type="primary", use_container_width=True):
        st.session_state["trip_id"] = trip_id
        st.query_params["trip_id"] = trip_id
        st.switch_page("pages/5_vote.py")

elif current_status == "complete":
    st.success("🏆 Voting is complete! The winner has been decided.")
    if st.button("View Results →", type="primary", use_container_width=True):
        st.session_state["trip_id"] = trip_id
        st.query_params["trip_id"] = trip_id
        st.switch_page("pages/5_vote.py")

elif not management_token:
    st.info("💡 The organiser will open the voting phase when everyone is ready. "
            "Check back soon or ask the organiser to share the voting link!")
