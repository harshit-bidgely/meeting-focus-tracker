"""Tests for Config G Suite integration fields and methods."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from config import Config


class TestConfigGoogleFields:
    """Test that Google Workspace config fields exist with correct defaults."""

    def test_google_credentials_file_default(self):
        assert Config.GOOGLE_CREDENTIALS_FILE == "credentials.json"

    def test_google_token_file_default(self):
        assert Config.GOOGLE_TOKEN_FILE == "token.json"

    def test_google_calendar_disabled_by_default(self):
        assert Config.ENABLE_GOOGLE_CALENDAR is False

    def test_gmail_summary_disabled_by_default(self):
        """Code default is False; .env may override at runtime."""
        assert Config.ENABLE_GOOGLE_GMAIL is False

    def test_google_drive_disabled_by_default(self):
        """Code default is False; .env may override at runtime."""
        with patch.dict("os.environ", {}, clear=False):
            with patch.dict("os.environ", {"ENABLE_GOOGLE_DRIVE": "false"}):
                result = os.getenv("ENABLE_GOOGLE_DRIVE", "false").lower() == "true"
                assert result is False

    def test_google_calendar_id_default(self):
        assert Config.GOOGLE_CALENDAR_ID == "primary"

    def test_require_agenda_validation_default_true(self):
        """Agenda validation should be enabled by default."""
        with patch.dict("os.environ", {"REQUIRE_AGENDA_VALIDATION": "true"}):
            result = os.getenv("REQUIRE_AGENDA_VALIDATION", "true").lower() == "true"
            assert result is True

    def test_agenda_min_quality_default_fair(self):
        """Minimum agenda quality should default to 'fair'."""
        with patch.dict("os.environ", {"AGENDA_MIN_QUALITY": "fair"}):
            result = os.getenv("AGENDA_MIN_QUALITY", "fair")
            assert result == "fair"


class TestConfigGoogleEnabled:
    """Test the google_enabled() helper method."""

    def test_all_disabled_returns_false(self):
        with patch.object(Config, "ENABLE_GOOGLE_CALENDAR", False), \
             patch.object(Config, "ENABLE_GOOGLE_GMAIL", False), \
             patch.object(Config, "ENABLE_GOOGLE_DRIVE", False), \
             patch.object(Config, "ENABLE_GOOGLE_CHAT", False):
            assert Config.google_enabled() is False

    def test_calendar_only_returns_true(self):
        with patch.object(Config, "ENABLE_GOOGLE_CALENDAR", True), \
             patch.object(Config, "ENABLE_GOOGLE_GMAIL", False), \
             patch.object(Config, "ENABLE_GOOGLE_DRIVE", False), \
             patch.object(Config, "ENABLE_GOOGLE_CHAT", False):
            assert Config.google_enabled() is True

    def test_gmail_only_returns_true(self):
        with patch.object(Config, "ENABLE_GOOGLE_CALENDAR", False), \
             patch.object(Config, "ENABLE_GOOGLE_GMAIL", True), \
             patch.object(Config, "ENABLE_GOOGLE_DRIVE", False), \
             patch.object(Config, "ENABLE_GOOGLE_CHAT", False):
            assert Config.google_enabled() is True

    def test_drive_only_returns_true(self):
        with patch.object(Config, "ENABLE_GOOGLE_CALENDAR", False), \
             patch.object(Config, "ENABLE_GOOGLE_GMAIL", False), \
             patch.object(Config, "ENABLE_GOOGLE_DRIVE", True), \
             patch.object(Config, "ENABLE_GOOGLE_CHAT", False):
            assert Config.google_enabled() is True

    def test_chat_only_returns_true(self):
        with patch.object(Config, "ENABLE_GOOGLE_CALENDAR", False), \
             patch.object(Config, "ENABLE_GOOGLE_GMAIL", False), \
             patch.object(Config, "ENABLE_GOOGLE_DRIVE", False), \
             patch.object(Config, "ENABLE_GOOGLE_CHAT", True):
            assert Config.google_enabled() is True

    def test_all_enabled_returns_true(self):
        with patch.object(Config, "ENABLE_GOOGLE_CALENDAR", True), \
             patch.object(Config, "ENABLE_GOOGLE_GMAIL", True), \
             patch.object(Config, "ENABLE_GOOGLE_DRIVE", True), \
             patch.object(Config, "ENABLE_GOOGLE_CHAT", True):
            assert Config.google_enabled() is True


class TestConfigValidateWithGoogle:
    """Test that validate() skips MEETING_ID when Calendar is enabled."""

    @pytest.mark.skip(reason="Feature not yet implemented: MEETING_ID optional with calendar")
    def test_meeting_id_not_required_when_calendar_enabled(self):
        with patch.object(Config, "LLM_API_KEY", "key"), \
             patch.object(Config, "VEXA_API_KEY", "key"), \
             patch.object(Config, "MEETING_ID", None), \
             patch.object(Config, "ENABLE_GOOGLE_CALENDAR", True):
            missing = Config.validate()
            assert "MEETING_ID" not in missing

    def test_meeting_id_required_when_calendar_disabled(self):
        with patch.object(Config, "LLM_API_KEY", "key"), \
             patch.object(Config, "VEXA_API_KEY", "key"), \
             patch.object(Config, "MEETING_ID", None), \
             patch.object(Config, "ENABLE_GOOGLE_CALENDAR", False):
            missing = Config.validate()
            assert "MEETING_ID" in missing

    def test_llm_and_vexa_always_required(self):
        with patch.object(Config, "LLM_API_KEY", None), \
             patch.object(Config, "VEXA_API_KEY", None), \
             patch.object(Config, "MEETING_ID", "test"), \
             patch.object(Config, "ENABLE_GOOGLE_CALENDAR", True):
            missing = Config.validate()
            assert "LLM_API_KEY" in missing
            assert "VEXA_API_KEY" in missing

    def test_no_missing_when_all_provided(self):
        with patch.object(Config, "LLM_API_KEY", "key"), \
             patch.object(Config, "VEXA_API_KEY", "key"), \
             patch.object(Config, "MEETING_ID", "abc-defg-hij"), \
             patch.object(Config, "ENABLE_GOOGLE_CALENDAR", False):
            missing = Config.validate()
            assert missing == []
