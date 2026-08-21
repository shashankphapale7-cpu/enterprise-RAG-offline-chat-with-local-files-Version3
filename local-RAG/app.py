"""
AI Memory OS — Enterprise Edition
Multi-user knowledge vault with authentication, tenant isolation, and multimodal ingestion.
"""

import streamlit as st
import embedding_utils
from auth import init_db, get_total_users

# ─── Page config (must be first Streamlit command) ────────────────────
st.set_page_config(
    page_title="AI Memory OS",
    page_icon=":material/neurology:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Initialize database (seeds users on first run) ──────────────────
init_db()

# ─── Session state initialization ────────────────────────────────────
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("username", None)

# ─── Build navigation based on auth state ─────────────────────────────
if not st.session_state.authenticated:
    # Unauthenticated: only show login
    page = st.navigation(
        [st.Page("app_pages/login.py", title="Sign in", icon=":material/login:")],
        position="top",
    )
else:
    # Authenticated: full navigation
    page = st.navigation(
        {
            "": [
                st.Page("app_pages/search.py", title="Memory search", icon=":material/search:"),
                st.Page("app_pages/ingest_page.py", title="Ingest files", icon=":material/upload_file:"),
                st.Page("app_pages/journal.py", title="Daily journal", icon=":material/edit_note:"),
            ],
            "Manage": [
                st.Page("app_pages/stats.py", title="Memory stats", icon=":material/analytics:"),
                st.Page("app_pages/settings.py", title="Settings", icon=":material/settings:"),
            ],
        },
        position="sidebar",
    )

# ─── Sidebar (shown only when authenticated) ─────────────────────────
if st.session_state.authenticated:
    with st.sidebar:
        st.caption(f":material/person: Signed in as **{st.session_state.username}**")

        if st.button(":material/logout: Sign out", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()

# ─── Title bar ────────────────────────────────────────────────────────
if st.session_state.authenticated:
    st.title(f"{page.icon} {page.title}")
else:
    st.title(":material/neurology: AI Memory OS")
    st.caption("Enterprise knowledge vault — multi-user, multimodal, offline")

# ─── Run the selected page ───────────────────────────────────────────
page.run()
