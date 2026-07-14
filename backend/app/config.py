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

    # Anthropic / Claude
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # Local fallback storage (used when USE_FIREBASE=false, e.g. local dev without creds yet)
    LOCAL_DATA_DIR: Path = BACKEND_DIR / "local_data"

    # Upload limits
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))


settings = Settings()
settings.LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
