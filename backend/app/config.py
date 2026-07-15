"""App configuration loaded from environment variables (.env)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = os.getenv(
        "FIREBASE_CREDENTIALS_PATH", str(BACKEND_DIR / "firebase-credentials.json")
    )
    USE_FIREBASE: bool = os.getenv("USE_FIREBASE", "false").lower() == "true"

    # Which AI provider powers contradiction detection, redlining, and Chat
    # with Contract's answer synthesis. "local" (default) runs entirely
    # on-machine, no API key, no cost, no external network call at inference
    # time -- but CPU-only inference is slow (see README Performance
    # section). "gemini" is an optional, openly-documented alternative for
    # when you have a Gemini API key and want faster responses -- it is NOT
    # a hidden default and NOT used unless you explicitly set this to
    # "gemini" and provide GEMINI_API_KEY below.
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "local").strip().lower()

    # Local LLM (used when AI_PROVIDER=local, the default) -- runs entirely
    # on-machine via llama-cpp-python. The GGUF file is downloaded once from
    # Hugging Face Hub on first use and cached locally (same pattern as the
    # Chat with Contract embedding model).
    #
    # Defaulting to the 7B model, not the smaller/faster 3B: verified directly
    # that the 3B model got a real, unambiguous contradiction (45-day vs
    # 15-day payment terms) WRONG, missing the deadline conflict entirely in
    # favor of an unrelated detail -- the 7B model (even at a more aggressive
    # Q3_K_M quantization) got the same case right, correctly citing both
    # the invoicing-frequency and the payment-deadline conflict. A fast but
    # unreliable contradiction detector defeats the point of this app, so
    # correctness won over download size/speed here. ~3.8GB one-time
    # download -- swap LOCAL_LLM_REPO_ID/LOCAL_LLM_FILENAME to the smaller
    # "Qwen/Qwen2.5-3B-Instruct-GGUF" / "qwen2.5-3b-instruct-q4_k_m.gguf" if
    # you need faster inference and can tolerate lower judgment quality.
    LOCAL_LLM_REPO_ID: str = os.getenv("LOCAL_LLM_REPO_ID", "Qwen/Qwen2.5-7B-Instruct-GGUF")
    LOCAL_LLM_FILENAME: str = os.getenv("LOCAL_LLM_FILENAME", "qwen2.5-7b-instruct-q3_k_m.gguf")
    LOCAL_LLM_CONTEXT_SIZE: int = int(os.getenv("LOCAL_LLM_CONTEXT_SIZE", "4096"))

    # Google / Gemini (only used when AI_PROVIDER=gemini). Both
    # "gemini-flash-latest" and "gemini-flash-lite-latest" are Google-
    # maintained aliases that always point at a current model -- pinning a
    # dated model name (e.g. "gemini-2.5-flash") risks it being retired for
    # new accounts later. Defaulting to the "lite" tier: on a free-tier key
    # the full flash tier was observed returning 503 "high demand" while
    # flash-lite responded reliably.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    # Local fallback storage (used when USE_FIREBASE=false, e.g. local dev without creds yet)
    LOCAL_DATA_DIR: Path = BACKEND_DIR / "local_data"

    # Upload limits
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))


settings = Settings()
settings.LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
