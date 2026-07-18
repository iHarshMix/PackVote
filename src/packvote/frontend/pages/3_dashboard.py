import streamlit as st
import httpx
import os
import threading
import json
import asyncio
import websockets
from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit.runtime import get_instance

st.set_page_config(page_title="Trip Progress Dashboard", page_icon="📊", layout="centered")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Custom header styling
st.markdown("""
<style>
    .header-style {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #2E7D32 0%, #4CAF50 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.5rem;
    }
    .participant-card {
        padding: 0.8rem;
        border-radius: 8px;
        background-color: #1E1E1E;
        border: 1px solid #333;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .badge-green {
        background-color: #2E7D32;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .badge-grey {
        background-color: #555;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-style">📊 Trip Progress Dashboard</div>', unsafe_allow_html=True)

# Retrieve trip_id from URL query params or session state fallback
trip_id = st.query_params.get("trip_id") or st.session_state.get("trip_id")
if not trip_id:
    st.error("Missing Trip ID in URL! Please access this page using the dashboard link.")
    st.stop()
else:
    # Sync back to session state and query params to preserve it
    st.session_state["trip_id"] = trip_id
    st.query_params["trip_id"] = trip_id

# Helper to fetch initial state via HTTP
def fetch_initial_data(trip_id):
    try:
        resp = httpx.get(f"{BACKEND_URL}/trips/{trip_id}/dashboard", timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
    return None

# Start background WebSocket listener thread
def start_listener(trip_id, session_id):
    def ws_thread():
        async def listen():
            # Format WebSocket URL from BACKEND_URL
            ws_proto = "ws://"
            if BACKEND_URL.startswith("https://"):
                ws_proto = "wss://"
            cleaned_backend = BACKEND_URL.replace("http://", "").replace("https://", "")
            uri = f"{ws_proto}{cleaned_backend}/ws/{trip_id}/status"
            
            while True:
                try:
                    async with websockets.connect(uri) as ws:
                        while True:
                            message = await ws.recv()
                            data = json.loads(message)
                            st.session_state[f"ws_data_{trip_id}"] = data
                            
                            # Trigger Streamlit rerun
                            runtime = get_instance()
                            session_info = runtime._session_mgr.get_active_session_info(session_id)
                            if session_info:
                                session_info.session.request_rerun(None)
                except Exception:
                    # Connection lost; sleep and retry
                    await asyncio.sleep(2)
                    
        asyncio.run(listen())

    thread = threading.Thread(target=ws_thread, daemon=True)
    add_script_run_ctx(thread)
    thread.start()

# Load initial data if not already present in session state
if f"ws_data_{trip_id}" not in st.session_state:
    init_data = fetch_initial_data(trip_id)
    if init_data:
        st.session_state[f"ws_data_{trip_id}"] = init_data
        
    # Start WebSocket thread listener
    from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
    ctx = get_script_run_ctx()
    if ctx:
        start_listener(trip_id, ctx.session_id)

# UI Fragment for auto-refreshing the status
@st.fragment(run_every=2.0)
def show_dashboard():
    data = st.session_state.get(f"ws_data_{trip_id}")
    if not data:
        st.info("Loading dashboard metrics...")
        return
        
    status = data.get("status")
    responded = data.get("responded_count", 0)
    total = data.get("total_count", 0)
    participants = data.get("participants", [])
    
    # 1. State details card
    status_badges = {
        "setup": "🔵 Setup (Adding participants)",
        "survey": "🟢 Survey Active (Swiping destinations)",
        "reveal": "🟡 AI recommendations ready!",
        "voting": "🟠 Voting Phase Active",
        "complete": "🟣 Trip Decided!"
    }
    
    with st.container(border=True):
        st.markdown(f"**Trip Status:** {status_badges.get(status, status.capitalize())}")
        
    st.write("")
    
    # 2. Survey progress tracker
    st.subheader("📝 Response Progress")
    progress_val = responded / total if total > 0 else 0.0
    st.progress(progress_val)
    st.write(f"🗳️ **{responded} out of {total}** participants have completed their swipes.")
    
    st.write("---")
    
    # 3. Participant status checklist
    st.subheader("👥 Participant List")
    for p in participants:
        name = p.get("name")
        has_responded = p.get("responded", False)
        
        status_badge = '<span class="badge-green">Responded</span>' if has_responded else '<span class="badge-grey">Pending</span>'
        
        st.markdown(f"""
        <div class="participant-card">
            <span>👤 {name}</span>
            {status_badge}
        </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    
    # 4. Action details depending on status
    if status == "reveal":
        st.success("🎉 All responses are in! The AI recommendation pipeline is complete.")
        
        from packvote.backend.core.database import SessionLocal
        from packvote.backend.models.db import Recommendation
        import uuid
        
        db = SessionLocal()
        try:
            recs = db.query(Recommendation).filter(Recommendation.trip_id == uuid.UUID(trip_id)).order_by(Recommendation.rank).all()
            if recs:
                st.subheader("💡 AI Travel Recommendations")
                for r in recs:
                    with st.container(border=True):
                        st.markdown(f"### Rank {r.rank}: **{r.destination}**")
                        st.write(f"💰 **Estimated Budget:** {r.budget_estimate} INR")
                        st.write(f"👍 **Why it fits:** {r.fit_reason}")
                        st.write(f"⚖️ **Tradeoff:** {r.tradeoff}")
            else:
                st.info("Generating recommendations... Refresh in a moment.")
        except Exception as e:
            st.error(f"Error loading recommendations: {e}")
        finally:
            db.close()
            
        if st.button("👁️ View Full Reveal & Open Voting", type="primary", use_container_width=True):
            st.session_state["trip_id"] = trip_id
            st.query_params["trip_id"] = trip_id
            st.switch_page("pages/4_reveal.py")
            
    elif status == "voting":
        st.info("🗳️ Voting is currently active for this trip.")
        if st.button("🗳️ Go to Voting Page", type="primary", use_container_width=True):
            st.session_state["trip_id"] = trip_id
            st.query_params["trip_id"] = trip_id
            st.switch_page("pages/5_vote.py")
            
    elif status == "complete":
        st.success("🏆 The winning destination has been decided!")
        if st.button("🎉 View Results", type="primary", use_container_width=True):
            st.session_state["trip_id"] = trip_id
            st.query_params["trip_id"] = trip_id
            st.switch_page("pages/5_vote.py")

show_dashboard()
