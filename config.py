from __future__ import annotations

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    # ── Core LLM ──────────────────────────────────────────────────────────
    LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    # ── Vexa ──────────────────────────────────────────────────────────────
    VEXA_API_KEY: str | None = os.getenv("VEXA_API_KEY")
    VEXA_API_BASE: str = os.getenv("VEXA_API_BASE", "https://api.cloud.vexa.ai")

    # ── Meeting ───────────────────────────────────────────────────────────
    MEETING_PLATFORM: str = os.getenv("MEETING_PLATFORM", "google_meet")
    MEETING_ID: str | None = os.getenv("MEETING_ID")
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
    DEVIATION_THRESHOLD: int = int(os.getenv("DEVIATION_THRESHOLD", "2"))
    ALERT_COOLDOWN: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "180"))
    CALENDAR_DESCRIPTION: str = os.getenv("CALENDAR_DESCRIPTION", "")

    # ── Post-meeting email (all optional — email is skipped if SMTP_HOST is blank) ──
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() != "false"
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
    # Comma-separated list of recipient email addresses
    EMAIL_RECIPIENTS: list[str] = [
        addr.strip()
        for addr in os.getenv("EMAIL_RECIPIENTS", "").split(",")
        if addr.strip()
    ]
    EMAIL_SUBJECT_PREFIX: str = os.getenv("EMAIL_SUBJECT_PREFIX", "Meeting Report")

    # ── History store ─────────────────────────────────────────────────────
    # Directory for persisting meeting summaries across sessions.
    # Defaults to .meeting_history/ next to the project root.
    HISTORY_DIR: str = os.getenv("HISTORY_DIR", "")

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

    @classmethod
    def email_enabled(cls) -> bool:
        """Return True only when the minimum SMTP config is present."""
        return bool(cls.SMTP_HOST and cls.EMAIL_SENDER and cls.EMAIL_RECIPIENTS)
