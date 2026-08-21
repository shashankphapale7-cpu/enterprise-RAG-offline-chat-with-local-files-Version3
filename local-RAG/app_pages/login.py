"""
AI Memory OS — Login page
"""

import streamlit as st
from auth import authenticate


st.header("Sign in to your account")
st.caption("Enter your credentials to access your knowledge vault.")

with st.form("login_form", clear_on_submit=False):
    username = st.text_input(
        "Username",
        placeholder="e.g. user1",
        key="login_username",
    )
    password = st.text_input(
        "Password",
        type="password",
        placeholder="Enter password",
        key="login_password",
    )
    submitted = st.form_submit_button("Sign in", type="primary")

if submitted:
    if not username or not password:
        st.error("Please enter both username and password.", icon=":material/error:")
    elif authenticate(username.strip().lower(), password):
        st.session_state.authenticated = True
        st.session_state.username = username.strip().lower()
        st.toast(f"Welcome back, {username}!", icon=":material/check_circle:")
        st.rerun()
    else:
        st.error("Invalid username or password.", icon=":material/error:")

st.caption("Default accounts: user1/password1, user2/password2, ... user1000/password1000")
