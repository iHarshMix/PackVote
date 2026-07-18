import streamlit as st
import os
import httpx
from datetime import datetime, timezone

st.set_page_config(page_title="Vote & Results", page_icon="🗳️")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Retrieve identifiers from URL or session state ───────────────────────────
trip_id = st.query_params.get("trip_id") or st.session_state.get("trip_id")
token = st.query_params.get("token") or st.session_state.get("token")

if not trip_id:
    st.error("Missing Trip ID! Please access this page from the reveal or dashboard page.")
    st.stop()
else:
    st.session_state["trip_id"] = trip_id
    st.query_params["trip_id"] = trip_id
if token:
    st.session_state["token"] = token
    st.query_params["token"] = token

# ── Helpers ──────────────────────────────────────────────────────────────────

def fetch_trip_status(tid):
    resp = httpx.get(f"{BACKEND_URL}/trips/{tid}/status", timeout=10.0)
    if resp.status_code == 200:
        return resp.json().get("status")
    return None

def fetch_reveal(tid):
    resp = httpx.get(f"{BACKEND_URL}/trips/{tid}/reveal", timeout=15.0)
    if resp.status_code == 200:
        return resp.json()
    return None

def fetch_result(tid):
    resp = httpx.get(f"{BACKEND_URL}/trips/{tid}/result", timeout=15.0)
    if resp.status_code == 200:
        return resp.json()
    return None

def fetch_dashboard(tid):
    resp = httpx.get(f"{BACKEND_URL}/trips/{tid}/dashboard", timeout=10.0)
    if resp.status_code == 200:
        return resp.json()
    return None

# ── Determine current state ─────────────────────────────────────────────────
current_status = fetch_trip_status(trip_id)

if current_status not in ("voting", "complete"):
    st.info("🗳️ Voting has not started yet for this trip. Please check back later!")
    if st.button("← Back to Reveal", use_container_width=True):
        st.switch_page("pages/4_reveal.py")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: RESULTS (if complete)
# ══════════════════════════════════════════════════════════════════════════════

if current_status == "complete":
    result = fetch_result(trip_id)
    if result:
        st.markdown("""
        <style>
        .winner-card {
            text-align: center;
            padding: 2rem;
            border-radius: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-bottom: 1.5rem;
        }
        .winner-name {
            font-size: 3rem;
            font-weight: 800;
            margin: 0.5rem 0;
        }
        .winner-label {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="winner-card">
            <div class="winner-label">🏆 THE WINNER IS</div>
            <div class="winner-name">{result['winner']}</div>
        </div>
        """, unsafe_allow_html=True)

        # Vote breakdown
        st.subheader("📊 Vote Breakdown")
        breakdown = result.get("vote_breakdown", {})
        if breakdown:
            import pandas as pd
            df = pd.DataFrame(
                [{"Destination": k, "First-Choice Votes": v} for k, v in breakdown.items()]
            ).sort_values("First-Choice Votes", ascending=False)
            st.bar_chart(df.set_index("Destination"))

        # AI Summary
        st.subheader("🤖 AI Summary")
        st.info(result.get("ai_summary", "No summary available."))

        # Share card
        st.divider()
        share_text = (
            f"🏆 PackVote Result: {result['winner']} won!\n"
            f"📊 {result.get('ai_summary', '')}\n"
            f"Planned with PackVote ✈️"
        )
        st.text_area("📋 Copy & share this result:", value=share_text, height=100)

    else:
        st.error("Could not load results.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: ACTIVE VOTING
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
.vote-header {
    text-align: center;
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.3rem;
}
.vote-sub {
    text-align: center;
    color: #aaa;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="vote-header">🗳️ Rank Your Destinations</div>', unsafe_allow_html=True)
st.markdown('<div class="vote-sub">Drag your favorites to the top — your ranking matters!</div>', unsafe_allow_html=True)

# ── Countdown Timer ──────────────────────────────────────────────────────────
dashboard_data = fetch_dashboard(trip_id)

# ── Vote Progress (blurred leaderboard) ──────────────────────────────────────
if dashboard_data:
    total = dashboard_data.get("total_count", 0)
    # Count voted participants from the dashboard (we need a separate count)
    # For now show the responded count from dashboard and note voting is active
    st.info(f"🗳️ Voting is active — cast your ranked-choice ballot below!")

# ── Fetch recommendations for the ballot ─────────────────────────────────────
reveal_data = fetch_reveal(trip_id)
if not reveal_data or not reveal_data.get("recommendations"):
    st.error("Could not load recommendations for voting.")
    st.stop()

recommendations = reveal_data["recommendations"]
candidate_names = [r["destination"] for r in recommendations]

# ── Initialize ranking in session state ──────────────────────────────────────
if "ranking" not in st.session_state:
    st.session_state["ranking"] = list(candidate_names)

if "vote_submitted" not in st.session_state:
    st.session_state["vote_submitted"] = False

# ── Reordering UI ────────────────────────────────────────────────────────────
if not st.session_state["vote_submitted"]:
    st.subheader("Your Ranking")
    st.caption("Use the buttons to reorder. #1 is your top choice.")

    ranking = st.session_state["ranking"]

    for idx, dest in enumerate(ranking):
        rec_info = next((r for r in recommendations if r["destination"] == dest), None)

        with st.container(border=True):
            cols = st.columns([1, 4, 1, 1])
            with cols[0]:
                st.markdown(f"### #{idx + 1}")
            with cols[1]:
                st.markdown(f"**{dest}**")
                if rec_info:
                    st.caption(f"₹{rec_info['budget_estimate']:,} · {rec_info['fit_reason'][:80]}...")
            with cols[2]:
                if idx > 0:
                    if st.button("⬆️", key=f"up_{idx}", use_container_width=True):
                        ranking[idx], ranking[idx - 1] = ranking[idx - 1], ranking[idx]
                        st.session_state["ranking"] = ranking
                        st.rerun()
            with cols[3]:
                if idx < len(ranking) - 1:
                    if st.button("⬇️", key=f"down_{idx}", use_container_width=True):
                        ranking[idx], ranking[idx + 1] = ranking[idx + 1], ranking[idx]
                        st.session_state["ranking"] = ranking
                        st.rerun()

    st.divider()

    # ── Submit Vote ──────────────────────────────────────────────────────
    if not token:
        st.warning("⚠️ No participant token found. You need to access this page via your unique link to vote.")
    else:
        if st.button("✅ Submit My Vote", type="primary", use_container_width=True):
            with st.spinner("Submitting your vote..."):
                try:
                    resp = httpx.post(
                        f"{BACKEND_URL}/votes",
                        json={
                            "participant_token": token,
                            "ranking": st.session_state["ranking"],
                        },
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        st.session_state["vote_submitted"] = True
                        st.success("🎉 Vote submitted successfully!")
                        result_data = resp.json()
                        st.info(f"📊 {result_data.get('voted_count', '?')}/{result_data.get('total_count', '?')} votes cast so far.")
                        st.balloons()
                        st.rerun()
                    else:
                        error_detail = resp.json().get("detail", resp.text)
                        st.error(f"Error: {error_detail}")
                except Exception as e:
                    st.error(f"Could not connect to backend: {e}")

else:
    st.success("✅ Your vote has been recorded! Waiting for other participants...")
    st.info("The results will be revealed once all votes are in or the timer expires. "
            "Refresh this page to check for updates.")

    # Check if results are ready
    if st.button("🔄 Check for Results", use_container_width=True):
        result = fetch_result(trip_id)
        if result:
            st.cache_data.clear()
            st.rerun()
        else:
            st.info("Voting is still active. Check back soon!")
