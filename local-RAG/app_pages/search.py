"""
AI Memory OS — Memory search page (tenant-scoped)
"""

import subprocess
import streamlit as st
import chromadb
from pathlib import Path
from embedding_utils import load_embedding_model, EMBEDDING_MODEL

# ─── Config ───────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
CHROMA_DIR = ROOT_DIR / "chroma_db"
COLLECTION_NAME = "memories"
OLLAMA_MODEL = "llama3.1:latest"


@st.cache_resource
def get_embed_model():
    return load_embedding_model(EMBEDDING_MODEL)


def get_chroma_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def run_ollama_query(prompt: str) -> str:
    try:
        res = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120
        )
        if res.returncode == 0:
            return res.stdout.strip()
        return f"Error: {res.stderr}"
    except Exception as e:
        return f"Execution error: {e}"


# ─── Page content ─────────────────────────────────────────────────────
username = st.session_state.username
embed_model = get_embed_model()
collection = get_chroma_collection()

st.caption("Query across your indexed documents, images, and spreadsheets.")

query = st.text_input(
    "Ask a question about your stored knowledge",
    placeholder="e.g. What are the project milestones in the Excel file?",
    label_visibility="collapsed",
)

col1, col2 = st.columns([1, 4])
with col1:
    top_k = st.slider("Top sources", 1, 20, 5)

if query:
    with st.spinner("Searching memories & generating answer..."):
        query_emb = embed_model.encode([query])[0].tolist()

        # Tenant-scoped search
        search_results = collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            where={"tenant_id": username},
            include=["documents", "metadatas", "distances"]
        )

        docs = search_results["documents"][0] if search_results["documents"] else []
        metas = search_results["metadatas"][0] if search_results["metadatas"] else []
        dists = search_results["distances"][0] if search_results["distances"] else []

        if not docs:
            st.warning("No relevant memories found. Try ingesting some files first.", icon=":material/search_off:")
        else:
            context_str = "\n\n---\n\n".join(
                [f"[From {m.get('source', 'unknown')}]: {d}" for d, m in zip(docs, metas)]
            )
            prompt = f"""You are an AI Memory Assistant for an enterprise knowledge base.
Answer using ONLY the provided memory context. Be precise and cite source files.
If the context contains spreadsheet/tabular data, present relevant data clearly.
If uncertain, state so clearly.

Context:
{context_str}

Question: {query}
Answer:"""

            answer = run_ollama_query(prompt)

            with st.container(border=True):
                st.subheader(":material/smart_toy: Answer")
                st.write(answer)

            st.subheader(":material/source: Source memories")
            for doc, meta, dist in zip(docs, metas, dists):
                relevance = max(0, (1 - dist) * 100)
                src = meta.get("source", "Unknown file")
                file_type = meta.get("file_type", "")

                # Icon based on file type
                icon = ":material/description:"
                if file_type in (".xlsx", ".xls", ".csv"):
                    icon = ":material/table_chart:"
                elif file_type == ".pdf":
                    icon = ":material/picture_as_pdf:"
                elif file_type in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
                    icon = ":material/image:"

                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"{icon} **{src}**")
                    with c2:
                        if relevance > 70:
                            st.badge(f"{relevance:.0f}% match", color="green")
                        elif relevance > 40:
                            st.badge(f"{relevance:.0f}% match", color="orange")
                        else:
                            st.badge(f"{relevance:.0f}% match", color="red")
                    st.caption(doc[:500] + ("..." if len(doc) > 500 else ""))
