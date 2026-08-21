"""
AI Memory OS — Memory stats & management page (tenant-scoped)
Supports recursive nested file listings and deletion.
"""

import os
import shutil
import streamlit as st
import chromadb
from pathlib import Path
from auth import get_user_data_dir

ROOT_DIR = Path(__file__).parent.parent
CHROMA_DIR = ROOT_DIR / "chroma_db"
COLLECTION_NAME = "memories"

# ─── Page content ─────────────────────────────────────────────────────
username = st.session_state.username


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def get_user_chunk_count(collection, tenant_id: str) -> int:
    """Count chunks belonging to a specific tenant."""
    try:
        results = collection.get(where={"tenant_id": tenant_id}, include=[])
        return len(results["ids"]) if results["ids"] else 0
    except Exception:
        return 0


def get_user_files(tenant_id: str) -> list[tuple[str, Path]]:
    """
    List files in user's data directory recursively.
    Returns list of (relative_path_str, absolute_path_obj).
    """
    user_dir = get_user_data_dir(tenant_id)
    files = []
    if user_dir.exists():
        for f in user_dir.rglob("*"):
            if f.is_file():
                try:
                    rel_path = str(f.relative_to(user_dir))
                except ValueError:
                    rel_path = f.name
                files.append((rel_path, f))
    return sorted(files, key=lambda x: x[0])


def delete_memory_by_source(collection, rel_path: str, abs_path: Path, tenant_id: str):
    """Delete all chunks originating from a specific file/relative path for a specific tenant."""
    try:
        results = collection.get(
            where={"$and": [{"source": rel_path}, {"tenant_id": tenant_id}]}
        )
        if results and results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass

    if abs_path.exists():
        os.remove(abs_path)


def clear_user_memories(collection, tenant_id: str):
    """Delete all chunks and files belonging to a tenant."""
    try:
        results = collection.get(where={"tenant_id": tenant_id}, include=[])
        if results and results["ids"]:
            batch_size = 500
            ids = results["ids"]
            for i in range(0, len(ids), batch_size):
                collection.delete(ids=ids[i:i + batch_size])
    except Exception:
        pass

    # Clear user's data directory recursively
    user_dir = get_user_data_dir(tenant_id)
    if user_dir.exists():
        for item in user_dir.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


# ─── Render ───────────────────────────────────────────────────────────
collection = get_collection()
user_files = get_user_files(username)
user_chunks = get_user_chunk_count(collection, username)

st.caption("Inspect your stored files, delete memories, or reset your knowledge vault.")

c1, c2 = st.columns(2)
with c1:
    st.metric("Your memory chunks", f"{user_chunks:,}")
with c2:
    st.metric("Your indexed files", f"{len(user_files):,}")

st.subheader(":material/delete: Delete specific file")

if user_files:
    file_map = {rel_path: abs_path for rel_path, abs_path in user_files}
    selected_file_rel = st.selectbox(
        "Select file to remove",
        list(file_map.keys()),
        label_visibility="collapsed",
    )

    if st.button(":material/delete: Delete selected memory"):
        abs_path = file_map[selected_file_rel]
        delete_memory_by_source(collection, selected_file_rel, abs_path, username)
        st.success(f"Deleted `{selected_file_rel}` and all associated chunks.", icon=":material/check_circle:")
        st.rerun()
else:
    st.caption("No files currently stored in your memory.")

st.subheader(":material/warning: Danger zone")
st.warning("This will permanently erase **all** your indexed chunks and data files.")

if st.button(":material/delete_forever: Wipe all my memories", type="primary"):
    clear_user_memories(collection, username)
    st.success("All your memories wiped clean!", icon=":material/check_circle:")
    st.rerun()
