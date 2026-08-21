"""
AI Memory OS — Daily journal page (tenant-scoped)
"""

import datetime
import streamlit as st
from pathlib import Path
from auth import get_user_data_dir

ROOT_DIR = Path(__file__).parent.parent

# ─── Page content ─────────────────────────────────────────────────────
username = st.session_state.username

st.caption("Capture thoughts and memory snippets — they're automatically indexed.")

today_str = datetime.date.today().strftime("%Y-%m-%d")
journal_text = st.text_area(
    f"Journal entry for {today_str}",
    height=200,
    placeholder="Write your notes here...",
)

if st.button(":material/save: Save & index note", type="primary"):
    if journal_text.strip():
        user_data_dir = get_user_data_dir(username)
        note_file = user_data_dir / f"{today_str}.txt"
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"\n--- [{timestamp}] ---\n{journal_text.strip()}\n"

        with open(note_file, "a", encoding="utf-8") as f:
            f.write(entry)

        from ingest import ingest
        ingest(data_dir=user_data_dir, show_progress=False, tenant_id=username)

        st.success(
            f"Journal entry saved to `{note_file.name}` and indexed into memory!",
            icon=":material/check_circle:",
        )
    else:
        st.warning("Journal entry cannot be empty.", icon=":material/warning:")
