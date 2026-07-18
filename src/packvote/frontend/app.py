import streamlit as st

st.set_page_config(page_title="PackVote - Group Travel Decider", page_icon="✈️", layout="centered")

# Custom styling for rich, premium aesthetics
st.markdown("""
<style>
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF8F00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .subtitle {
        font-size: 1.4rem;
        color: #888;
        margin-bottom: 2.5rem;
        text-align: center;
        font-weight: 500;
    }
    .feature-card {
        border-radius: 12px;
        padding: 1.5rem;
        background-color: #1E1E1E;
        border: 1px solid #333;
        margin-bottom: 1rem;
        height: 180px;
    }
    .feature-card h4 {
        margin-top: 0;
        color: #FF8F00;
        font-size: 1.2rem;
    }
    .feature-card p {
        color: #CCC;
        font-size: 0.95rem;
        line-height: 1.4;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">✈️ PackVote</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Decide your next group trip without the endless debate!</div>', unsafe_allow_html=True)

st.markdown("""
PackVote makes group travel planning fun, fast, and democratic. 
No more endless WhatsApp debates or spreadsheet madness. Participants swipe destinations, 
and our AI pipeline recommends the absolute best travel options matching everyone's budgets and dates.
""")

st.write("---")

st.markdown("### 🗺️ How It Works")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>1. Create a Trip</h4>
        <p>Organiser creates the trip, invites friends, and collects emails for recovery links.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <h4>3. AI Recommendation</h4>
        <p>Our LangGraph pipeline aggregates budgets, dates, and swipes to fetch and rank the perfect options.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>2. Swipe Survey</h4>
        <p>Friends swipe yes/no on curated destination cards, specify dates, and set their maximum budgets.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <h4>4. Ranked-Choice Vote</h4>
        <p>Vote on the final 3 AI recommendations. Instant-runoff voting determines the absolute winner.</p>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Action Form
st.subheader("🚀 Get Started")

if st.button("🆕 Create a New Trip", type="primary", use_container_width=True):
    st.switch_page("pages/1_organiser.py")

st.write("Already have a trip token? Use the recovery or survey links provided by your organiser, or navigate via the sidebar.")
