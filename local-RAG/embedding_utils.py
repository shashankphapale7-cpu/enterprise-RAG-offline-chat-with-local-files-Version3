"""
AI Memory OS — Embedding Model Utilities & Robust Client Patch
Fixes httpx / huggingface_hub client lifecycle issues in Streamlit and multi-threaded environments.
"""

import os
import huggingface_hub.utils._http as hf_http
from sentence_transformers import SentenceTransformer

# Default model used across AI Memory OS
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def patch_hf_hub_client():
    """
    Patch huggingface_hub.utils._http.get_session to handle closed httpx clients gracefully.
    In Streamlit / multi-threaded apps, httpx clients can be closed on script reruns or thread exit.
    If get_session returns a closed client, httpx raises:
      RuntimeError: Cannot send a request, as the client has been closed.
    This patch recreates the client automatically if it is closed.
    """
    if getattr(hf_http.get_session, "_is_patched", False):
        return

    def safe_get_session():
        if hf_http._GLOBAL_CLIENT is None or getattr(hf_http._GLOBAL_CLIENT, "is_closed", False):
            with hf_http._CLIENT_LOCK:
                hf_http._GLOBAL_CLIENT = hf_http._GLOBAL_CLIENT_FACTORY()
        return hf_http._GLOBAL_CLIENT

    safe_get_session._is_patched = True
    hf_http.get_session = safe_get_session


# Apply patch immediately on module import
patch_hf_hub_client()


def load_embedding_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    """
    Safely load a SentenceTransformer model.
    Tries offline mode (local_files_only=True) first for speed and reliability,
    and falls back to online load/download with the patched HF HTTP client.
    """
    patch_hf_hub_client()
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except Exception:
        # Fallback if model files are not yet in local HuggingFace cache
        return SentenceTransformer(model_name)
