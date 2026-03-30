from __future__ import annotations

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    VEXA_API_KEY: str | None = os.getenv("VEXA_API_KEY")
    VEXA_API_BASE: str = os.getenv("VEXA_API_BASE", "https://api.cloud.vexa.ai")
    MEETING_PLATFORM: str = os.getenv("MEETING_PLATFORM", "google_meet")
    MEETING_ID: str | None = os.getenv("MEETING_ID")
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
    DEVIATION_THRESHOLD: int = int(os.getenv("DEVIATION_THRESHOLD", "2"))
    ALERT_COOLDOWN: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "180"))
    CALENDAR_DESCRIPTION: str = os.getenv("CALENDAR_DESCRIPTION", "")
    MEMORY_STORAGE_PATH: str = os.getenv(
        "MEMORY_STORAGE_PATH",
        os.path.join(os.path.expanduser("~"), ".meeting_focus_tracker", "meeting_history.json"),
    )
    MEMORY_SIMILARITY_THRESHOLD: float = float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.55"))

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing required config keys."""
        missing = []
        if not cls.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        if not cls.VEXA_API_KEY:
            missing.append("VEXA_API_KEY")
        if not cls.MEETING_ID:
            missing.append("MEETING_ID")
        return missing
