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

    # Local LLM (contradiction detection, redlining, Chat with Contract
    # answer synthesis) -- runs entirely on-machine via llama-cpp-python, no
    # API key, no external network call at inference time. The GGUF file is
    # downloaded once from Hugging Face Hub on first use and cached locally
    # (same pattern as the Chat with Contract embedding model).
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

    # Local fallback storage (used when USE_FIREBASE=false, e.g. local dev without creds yet)
    LOCAL_DATA_DIR: Path = BACKEND_DIR / "local_data"

    # Upload limits
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))


settings = Settings()
settings.LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
