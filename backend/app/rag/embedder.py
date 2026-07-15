"""Local embedding model for the RAG chat feature (Chat with Contract).

Deliberately not routed through app/services/ai_client.py: embedding is a
retrieval-infrastructure concern, not a judgment call, and uses a different
local model (BAAI/bge-large-en-v1.5 via sentence-transformers) than the
judgment/generation model in app/services/local_llm_client.py. Both run
entirely on-machine: no API key, no per-call cost, no rate limits.
The model is downloaded once (~1.3GB) and cached by sentence-transformers/
huggingface_hub in the user's local cache directory on first use.

FastAPI runs sync endpoints in a thread pool, so concurrent Chat with
Contract requests can reach this module concurrently -- the same class of
bug found and fixed in local_llm_client.py and app/firebase.py. Two threads
racing the `_model is None` check could both construct a SentenceTransformer
at once, or both call .encode() on it concurrently; verified this crashed
the backend process the same way the unlocked Llama singleton did.
_model_lock serializes both model construction and every encode() call.
"""
from __future__ import annotations

import threading

import numpy as np
from sentence_transformers import SentenceTransformer

_EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"

# BGE's documented convention: prefix QUERIES (not documents/passages) with
# this instruction for retrieval tasks -- meaningfully improves retrieval
# quality for this model family. Document-side (clause) embeddings get no
# prefix; only embed_query() applies it.
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
    return _model


def embed_passages(texts: list[str]) -> np.ndarray:
    """Embeds clause text for indexing. Returns a (len(texts), 1024) float32
    array, L2-normalized (so inner product == cosine similarity)."""
    if not texts:
        return np.zeros((0, 1024), dtype="float32")
    model = _get_model()
    with _model_lock:
        return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True).astype("float32")


def embed_query(text: str) -> np.ndarray:
    """Embeds a user question for retrieval, with BGE's query instruction
    prefix. Returns a (1024,) float32 vector, L2-normalized."""
    model = _get_model()
    with _model_lock:
        embedding = model.encode([_QUERY_INSTRUCTION + text], normalize_embeddings=True, convert_to_numpy=True)
    return embedding[0].astype("float32")
