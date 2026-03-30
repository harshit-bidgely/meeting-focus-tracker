"""Tests for the Google OAuth2 authentication helper."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch, mock_open

import pytest

from services.google_auth import get_google_credentials, SCOPES, DEFAULT_CREDENTIALS_FILE, DEFAULT_TOKEN_FILE


class TestGetGoogleCredentials:
    """Test OAuth2 credential loading and flow."""

    def test_missing_credentials_file_raises(self, tmp_path):
        """Should raise FileNotFoundError if credentials.json doesn't exist."""
        fake_path = str(tmp_path / "nonexistent.json")
        with pytest.raises(FileNotFoundError, match="Google OAuth credentials file not found"):
            get_google_credentials(credentials_file=fake_path)

    def test_scopes_include_calendar_gmail_drive(self):
        """All three required scopes should be present."""
        assert "https://www.googleapis.com/auth/calendar.readonly" in SCOPES
        assert "https://www.googleapis.com/auth/gmail.send" in SCOPES
        assert "https://www.googleapis.com/auth/drive.file" in SCOPES

    def test_scopes_count(self):
        """Exactly 3 scopes should be defined."""
        assert len(SCOPES) == 3

    @patch("services.google_auth.InstalledAppFlow")
    @patch("services.google_auth.os.path.exists")
    def test_new_auth_flow_when_no_token(self, mock_exists, mock_flow_cls, tmp_path):
        """When no token.json exists, should run the OAuth flow."""
        creds_file = str(tmp_path / "credentials.json")
        token_file = str(tmp_path / "token.json")

        # credentials.json exists, token.json does not
        def exists_side_effect(path):
            if path == creds_file:
                return True
            return False
        mock_exists.side_effect = exists_side_effect

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = '{"token": "test"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_secrets_file.return_value = mock_flow

        result = get_google_credentials(credentials_file=creds_file, token_file=token_file)

        mock_flow_cls.from_client_secrets_file.assert_called_once_with(creds_file, SCOPES)
        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert result == mock_creds

    @patch("services.google_auth.Credentials")
    @patch("services.google_auth.os.path.exists")
    def test_loads_cached_token_when_valid(self, mock_exists, mock_creds_cls, tmp_path):
        """When token.json exists and is valid, should load it without re-auth."""
        creds_file = str(tmp_path / "credentials.json")
        token_file = str(tmp_path / "token.json")

        mock_exists.return_value = True  # Both files exist

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        result = get_google_credentials(credentials_file=creds_file, token_file=token_file)

        mock_creds_cls.from_authorized_user_file.assert_called_once_with(token_file, SCOPES)
        assert result == mock_creds

    @patch("services.google_auth.Request")
    @patch("services.google_auth.Credentials")
    @patch("services.google_auth.os.path.exists")
    def test_refreshes_expired_token(self, mock_exists, mock_creds_cls, mock_request_cls, tmp_path):
        """When token exists but is expired, should refresh it."""
        creds_file = str(tmp_path / "credentials.json")
        token_file = str(tmp_path / "token.json")

        mock_exists.return_value = True

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token-123"
        mock_creds.to_json.return_value = '{"token": "refreshed"}'
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        result = get_google_credentials(credentials_file=creds_file, token_file=token_file)

        mock_creds.refresh.assert_called_once()
        assert result == mock_creds

    def test_default_file_names(self):
        """Default file names should be credentials.json and token.json."""
        assert DEFAULT_CREDENTIALS_FILE == "credentials.json"
        assert DEFAULT_TOKEN_FILE == "token.json"
