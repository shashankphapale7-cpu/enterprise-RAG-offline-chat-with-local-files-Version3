"""
AI Memory OS — Settings page (password change)
"""

import streamlit as st
from auth import change_password, get_user_info

# ─── Page content ─────────────────────────────────────────────────────
username = st.session_state.username

st.caption("Manage your account settings.")

# Account info
user_info = get_user_info(username)
if user_info:
    with st.container(border=True):
        st.markdown(f":material/person: **Username:** `{user_info['username']}`")
        st.markdown(f":material/calendar_today: **Account created:** `{user_info['created_at'] or 'N/A'}`")
        st.markdown(f":material/schedule: **Last login:** `{user_info['last_login'] or 'N/A'}`")

st.subheader(":material/lock: Change password")

with st.form("change_password_form", clear_on_submit=True):
    current_pw = st.text_input(
        "Current password",
        type="password",
        placeholder="Enter current password",
    )
    new_pw = st.text_input(
        "New password",
        type="password",
        placeholder="Enter new password (min 4 characters)",
    )
    confirm_pw = st.text_input(
        "Confirm new password",
        type="password",
        placeholder="Re-enter new password",
    )
    submitted = st.form_submit_button(":material/save: Update password", type="primary")

if submitted:
    if not current_pw or not new_pw or not confirm_pw:
        st.error("All fields are required.", icon=":material/error:")
    elif new_pw != confirm_pw:
        st.error("New passwords do not match.", icon=":material/error:")
    else:
        success, message = change_password(username, current_pw, new_pw)
        if success:
            st.success(message, icon=":material/check_circle:")
        else:
            st.error(message, icon=":material/error:")
