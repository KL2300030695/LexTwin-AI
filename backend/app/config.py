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

    # Which AI provider powers contradiction detection + redline generation.
    # "claude" (default) or "gemini" -- see app/services/ai_client.py.
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "claude").strip().lower()

    # Anthropic / Claude
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # Google / Gemini (only used when AI_PROVIDER=gemini). Both
    # "gemini-flash-latest" and "gemini-flash-lite-latest" are Google-
    # maintained aliases that always point at a current model -- pinning a
    # dated model name (e.g. "gemini-2.5-flash") risks it being retired for
    # new accounts later, as already happened once during this project.
    # Defaulting to the "lite" tier: on a free-tier key the full flash tier
    # was observed returning 503 "high demand" while flash-lite responded
    # reliably -- swap back to gemini-flash-latest once on a paid plan.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    # Local fallback storage (used when USE_FIREBASE=false, e.g. local dev without creds yet)
    LOCAL_DATA_DIR: Path = BACKEND_DIR / "local_data"

    # Upload limits
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))


settings = Settings()
settings.LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
