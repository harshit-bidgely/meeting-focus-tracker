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

    # Google Workspace integration
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_TOKEN_FILE: str = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    ENABLE_GOOGLE_CALENDAR: bool = os.getenv("ENABLE_GOOGLE_CALENDAR", "false").lower() == "true"
    ENABLE_GMAIL_SUMMARY: bool = os.getenv("ENABLE_GMAIL_SUMMARY", "false").lower() == "true"
    ENABLE_GOOGLE_DRIVE: bool = os.getenv("ENABLE_GOOGLE_DRIVE", "false").lower() == "true"
    ENABLE_GOOGLE_CHAT: bool = os.getenv("ENABLE_GOOGLE_CHAT", "false").lower() == "true"
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    # Agenda enforcement
    REQUIRE_AGENDA_VALIDATION: bool = os.getenv("REQUIRE_AGENDA_VALIDATION", "true").lower() == "true"
    AGENDA_MIN_QUALITY: str = os.getenv("AGENDA_MIN_QUALITY", "fair")  # poor|fair|good|excellent

    # Auto mode — bot auto-joins meetings from calendar
    AUTO_JOIN_LEAD_MINUTES: int = int(os.getenv("AUTO_JOIN_LEAD_MINUTES", "2"))
    CALENDAR_POLL_INTERVAL: int = int(os.getenv("CALENDAR_POLL_INTERVAL", "30"))

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing required config keys."""
        missing = []
        if not cls.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        if not cls.VEXA_API_KEY:
            missing.append("VEXA_API_KEY")
        # MEETING_ID is only required if Google Calendar auto-fetch is disabled
        if not cls.MEETING_ID and not cls.ENABLE_GOOGLE_CALENDAR:
            missing.append("MEETING_ID")
        return missing

    @classmethod
    def google_enabled(cls) -> bool:
        """Return True if any Google Workspace integration is enabled."""
        return (
            cls.ENABLE_GOOGLE_CALENDAR
            or cls.ENABLE_GMAIL_SUMMARY
            or cls.ENABLE_GOOGLE_DRIVE
            or cls.ENABLE_GOOGLE_CHAT
        )
