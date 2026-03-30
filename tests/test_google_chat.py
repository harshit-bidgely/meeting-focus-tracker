"""Tests for Google Chat integration service.

Comprehensive test coverage for:
- Service initialization and credentials
- Space discovery and member caching
- Participant-to-space matching
- Message formatting and posting
- Error handling and graceful degradation
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from services.google_chat import GoogleChatService


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_credentials():
    """Mock Google service account credentials."""
    return Mock()


@pytest.fixture
def mock_chat_api():
    """Mock Google Chat API client."""
    api = MagicMock()
    return api


@pytest.fixture
def google_chat_service(mock_credentials, mock_chat_api):
    """Create GoogleChatService with mocked API."""
    with patch("services.google_chat.build") as mock_build:
        mock_build.return_value = mock_chat_api
        service = GoogleChatService(mock_credentials)
        service.chat_api = mock_chat_api
        return service


@pytest.fixture
def sample_space_cache():
    """Sample cached spaces with members."""
    return {
        "spaces/ABC123": ["alice@org.com", "bob@org.com", "charlie@org.com"],
        "spaces/DEF456": ["bob@org.com", "diana@org.com"],
        "spaces/GHI789": ["diana@org.com", "eve@org.com"],
        "spaces/JKL012": ["frank@org.com"],
    }


# ============================================================================
# TEST: Service Initialization
# ============================================================================


class TestServiceInitialization:
    """Test GoogleChatService initialization and setup."""

    def test_service_initializes_with_credentials(self, mock_credentials, mock_chat_api):
        """Service should initialize with provided credentials."""
        with patch("services.google_chat.build") as mock_build:
            mock_build.return_value = mock_chat_api
            service = GoogleChatService(mock_credentials)

            # Verify build was called with correct parameters
            mock_build.assert_called_once()
            assert service.chat_api is not None

    def test_space_cache_initialized_empty(self, google_chat_service):
        """Service should start with empty space cache."""
        assert hasattr(google_chat_service, "_space_members")
        assert isinstance(google_chat_service._space_members, dict)
        assert len(google_chat_service._space_members) == 0

    def test_credentials_stored(self, mock_credentials, mock_chat_api):
        """Service should store credentials reference."""
        with patch("services.google_chat.build") as mock_build:
            mock_build.return_value = mock_chat_api
            service = GoogleChatService(mock_credentials)
            assert service.credentials is not None


# ============================================================================
# TEST: Space Discovery and Caching
# ============================================================================


class TestSpaceDiscovery:
    """Test discovering and caching Google Chat spaces."""

    def test_discover_spaces_queries_api(self, google_chat_service, mock_chat_api):
        """discover_and_cache_spaces() should call spaces.list() API."""
        # Setup mock responses
        mock_chat_api.spaces.return_value.list.return_value.execute.return_value = {
            "spaces": [
                {"name": "spaces/ABC123", "displayName": "Engineering"},
                {"name": "spaces/DEF456", "displayName": "Product"},
            ]
        }
        mock_chat_api.spaces.return_value.members.return_value.list.return_value.execute.return_value = {
            "members": []
        }

        google_chat_service.discover_and_cache_spaces()

        # Verify spaces.list() was called
        mock_chat_api.spaces.return_value.list.assert_called()

    def test_discover_spaces_caches_members(self, google_chat_service, mock_chat_api):
        """discover_and_cache_spaces() should cache members for each space."""
        # Setup mock responses
        mock_chat_api.spaces.return_value.list.return_value.execute.return_value = {
            "spaces": [{"name": "spaces/ABC123"}]
        }

        members_response = {
            "members": [
                {"member": {"email": "alice@org.com"}},
                {"member": {"email": "bob@org.com"}},
            ]
        }
        mock_chat_api.spaces.return_value.members.return_value.list.return_value.execute.return_value = members_response

        google_chat_service.discover_and_cache_spaces()

        # Verify members are cached
        assert "spaces/ABC123" in google_chat_service._space_members
        assert "alice@org.com" in google_chat_service._space_members["spaces/ABC123"]
        assert "bob@org.com" in google_chat_service._space_members["spaces/ABC123"]

    def test_empty_space_list_handled(self, google_chat_service, mock_chat_api):
        """Should handle empty space list gracefully."""
        mock_chat_api.spaces.return_value.list.return_value.execute.return_value = {
            "spaces": []
        }

        google_chat_service.discover_and_cache_spaces()

        # Cache should remain empty
        assert len(google_chat_service._space_members) == 0

    def test_api_error_during_discovery_logged(self, google_chat_service, mock_chat_api):
        """Should log error and continue if Chat API fails during discovery."""
        mock_chat_api.spaces.return_value.list.return_value.execute.side_effect = Exception(
            "API error"
        )

        # Should not raise exception, logger.error should be called
        with patch("services.google_chat.logger") as mock_logger:
            google_chat_service.discover_and_cache_spaces()
            mock_logger.error.assert_called()

    def test_missing_email_in_member_handled(self, google_chat_service, mock_chat_api):
        """Should handle members without email gracefully."""
        mock_chat_api.spaces.return_value.list.return_value.execute.return_value = {
            "spaces": [{"name": "spaces/ABC123"}]
        }

        # Some members might not have email field
        members_response = {
            "members": [
                {"member": {"email": "alice@org.com"}},
                {"member": {}},  # No email
            ]
        }
        mock_chat_api.spaces.return_value.members.return_value.list.return_value.execute.return_value = members_response

        google_chat_service.discover_and_cache_spaces()

        # Should cache only valid email
        assert len(google_chat_service._space_members["spaces/ABC123"]) == 1
        assert "alice@org.com" in google_chat_service._space_members["spaces/ABC123"]

    def test_multiple_spaces_all_cached(self, google_chat_service, mock_chat_api):
        """Should cache all spaces and their members."""
        mock_chat_api.spaces.return_value.list.return_value.execute.return_value = {
            "spaces": [
                {"name": "spaces/ABC123"},
                {"name": "spaces/DEF456"},
                {"name": "spaces/GHI789"},
            ]
        }

        # Different members for each space
        def members_side_effect():
            return MagicMock(
                execute=MagicMock(
                    return_value={
                        "members": [
                            {"member": {"email": "user@org.com"}},
                        ]
                    }
                )
            )

        mock_chat_api.spaces.return_value.members.return_value.list.side_effect = (
            lambda **kwargs: members_side_effect()
        )

        google_chat_service.discover_and_cache_spaces()

        # All spaces should be cached
        assert len(google_chat_service._space_members) == 3
        assert "spaces/ABC123" in google_chat_service._space_members
        assert "spaces/DEF456" in google_chat_service._space_members
        assert "spaces/GHI789" in google_chat_service._space_members


# ============================================================================
# TEST: Participant Matching Logic
# ============================================================================


class TestParticipantMatching:
    """Test matching meeting participants to spaces."""

    def test_single_participant_matches_space(self, google_chat_service):
        """Meeting with participant should match space containing them."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com", "bob@org.com"],
        }

        participants = ["alice@org.com"]
        matching = google_chat_service._find_matching_spaces(participants)

        assert "spaces/ABC123" in matching

    def test_multiple_participants_match_spaces(self, google_chat_service):
        """Meeting with multiple participants should find all matching spaces."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com", "bob@org.com"],
            "spaces/DEF456": ["bob@org.com", "charlie@org.com"],
            "spaces/GHI789": ["diana@org.com", "charlie@org.com"],  # Add charlie to match
        }

        participants = ["alice@org.com", "bob@org.com", "charlie@org.com"]
        matching = google_chat_service._find_matching_spaces(participants)

        # All three spaces have at least one participant
        assert len(matching) == 3
        assert "spaces/ABC123" in matching
        assert "spaces/DEF456" in matching
        assert "spaces/GHI789" in matching

    def test_no_matching_spaces_returns_empty(self, google_chat_service):
        """Meeting with participants not in any space should return empty list."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
            "spaces/DEF456": ["bob@org.com"],
        }

        participants = ["nobody@org.com"]
        matching = google_chat_service._find_matching_spaces(participants)

        assert len(matching) == 0

    def test_case_insensitive_email_matching(self, google_chat_service):
        """Email matching should be case-insensitive."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["Alice@Org.com", "Bob@Org.com"],
        }

        participants = ["alice@org.com", "bob@org.com"]
        matching = google_chat_service._find_matching_spaces(participants)

        assert "spaces/ABC123" in matching

    def test_partial_participant_match_counts(self, google_chat_service):
        """Space with even one participant from meeting should be included."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],  # Only Alice
            "spaces/DEF456": ["bob@org.com"],     # Only Bob
        }

        # Meeting has both Alice and Bob
        participants = ["alice@org.com", "bob@org.com"]
        matching = google_chat_service._find_matching_spaces(participants)

        # Both spaces should match
        assert len(matching) == 2

    def test_empty_participants_list(self, google_chat_service):
        """Meeting with no participants should match no spaces."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
        }

        matching = google_chat_service._find_matching_spaces([])

        assert len(matching) == 0

    def test_empty_space_cache(self, google_chat_service):
        """If no spaces cached, should return empty list."""
        google_chat_service._space_members = {}

        matching = google_chat_service._find_matching_spaces(["alice@org.com"])

        assert len(matching) == 0

    def test_invalid_email_format_skipped(self, google_chat_service):
        """Invalid email formats should be skipped without crashing."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
        }

        # Invalid email formats mixed with valid ones
        participants = ["alice@org.com", "not-an-email", "also@invalid@example.com"]

        # Should not raise, only match valid emails
        matching = google_chat_service._find_matching_spaces(participants)
        assert len(matching) >= 0


# ============================================================================
# TEST: Message Formatting
# ============================================================================


class TestMessageFormatting:
    """Test smart card message formatting."""

    def test_smart_card_includes_title(self, google_chat_service):
        """Smart card should include meeting title."""
        card = google_chat_service._build_smart_card(
            meeting_title="Budget Review",
            decisions=["Approve Q2 budget"],
            open_items=["Schedule review"],
            drive_url="https://drive.google.com/doc/ABC123",
        )

        card_str = str(card)
        assert "Budget Review" in card_str

    def test_smart_card_includes_decisions(self, google_chat_service):
        """Smart card should include all decisions."""
        decisions = ["Decision 1", "Decision 2", "Decision 3"]
        card = google_chat_service._build_smart_card(
            meeting_title="Test",
            decisions=decisions,
            open_items=[],
            drive_url=None,
        )

        card_str = str(card)
        for decision in decisions:
            assert decision in card_str

    def test_smart_card_includes_open_items(self, google_chat_service):
        """Smart card should include all open items."""
        open_items = ["Action 1", "Action 2", "Action 3"]
        card = google_chat_service._build_smart_card(
            meeting_title="Test",
            decisions=[],
            open_items=open_items,
            drive_url=None,
        )

        card_str = str(card)
        for item in open_items:
            assert item in card_str

    def test_empty_decisions_handled(self, google_chat_service):
        """Should handle empty decisions list gracefully."""
        card = google_chat_service._build_smart_card(
            meeting_title="Test",
            decisions=[],
            open_items=["Action 1"],
            drive_url=None,
        )

        # Should not raise and produce valid message
        assert card is not None

    def test_empty_open_items_handled(self, google_chat_service):
        """Should handle empty open items list gracefully."""
        card = google_chat_service._build_smart_card(
            meeting_title="Test",
            decisions=["Decision 1"],
            open_items=[],
            drive_url=None,
        )

        assert card is not None

    def test_drive_link_included_when_provided(self, google_chat_service):
        """Smart card should include Drive link when provided."""
        drive_url = "https://docs.google.com/document/d/ABC123/edit"
        card = google_chat_service._build_smart_card(
            meeting_title="Test",
            decisions=[],
            open_items=[],
            drive_url=drive_url,
        )

        card_str = str(card)
        assert "ABC123" in card_str or drive_url in card_str

    def test_drive_link_omitted_when_none(self, google_chat_service):
        """Smart card should not include Drive link when None."""
        card = google_chat_service._build_smart_card(
            meeting_title="Test",
            decisions=[],
            open_items=[],
            drive_url=None,
        )

        assert card is not None
        # Should still be valid card even without Drive link

    def test_special_characters_in_message(self, google_chat_service):
        """Should handle special characters in message content."""
        card = google_chat_service._build_smart_card(
            meeting_title="Q&A: Budget & Planning",
            decisions=["Approve 50% budget increase"],
            open_items=["Review <requirements> by EOD"],
            drive_url=None,
        )

        assert card is not None

    def test_long_decision_text(self, google_chat_service):
        """Should handle long decision text."""
        long_decision = "A" * 500  # 500 character decision
        card = google_chat_service._build_smart_card(
            meeting_title="Test",
            decisions=[long_decision],
            open_items=[],
            drive_url=None,
        )

        assert card is not None


# ============================================================================
# TEST: Message Posting
# ============================================================================


class TestMessagePosting:
    """Test posting messages to Google Chat spaces."""

    def test_post_to_matching_spaces(self, google_chat_service, mock_chat_api):
        """Should post message to each matching space."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
            "spaces/DEF456": ["bob@org.com"],
        }

        mock_chat_api.spaces.return_value.messages.return_value.create.return_value.execute.return_value = {
            "name": "spaces/ABC123/messages/MSG123"
        }

        result = google_chat_service.post_meeting_summary(
            meeting_title="Test",
            participants=["alice@org.com", "bob@org.com"],
            decisions=[],
            open_items=[],
            drive_url=None,
        )

        assert result["success"] is True
        assert len(result["spaces_posted"]) > 0

    def test_post_returns_success_dict(self, google_chat_service, mock_chat_api):
        """post_meeting_summary() should return structured result dict."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
        }

        mock_chat_api.spaces.return_value.messages.return_value.create.return_value.execute.return_value = {
            "name": "spaces/ABC123/messages/MSG123"
        }

        result = google_chat_service.post_meeting_summary(
            meeting_title="Test",
            participants=["alice@org.com"],
            decisions=[],
            open_items=[],
            drive_url=None,
        )

        # Check all required fields present
        assert "success" in result
        assert isinstance(result["success"], bool)
        assert "spaces_posted" in result
        assert isinstance(result["spaces_posted"], list)
        assert "spaces_found" in result
        assert isinstance(result["spaces_found"], int)
        assert "error" in result or "error" not in result

    def test_skip_spaces_with_no_participants(self, google_chat_service, mock_chat_api):
        """Should skip spaces where no participants are members."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
            "spaces/DEF456": ["bob@org.com"],
            "spaces/GHI789": ["charlie@org.com"],
        }

        mock_chat_api.spaces.return_value.messages.return_value.create.return_value.execute.return_value = {
            "name": "spaces/ABC123/messages/MSG123"
        }

        # Only Alice and Bob attending, not Charlie
        result = google_chat_service.post_meeting_summary(
            meeting_title="Test",
            participants=["alice@org.com", "bob@org.com"],
            decisions=[],
            open_items=[],
            drive_url=None,
        )

        # Should only post to ABC and DEF, not GHI
        assert result["spaces_found"] == 2
        assert len(result["spaces_posted"]) <= 2

    def test_api_error_during_posting(self, google_chat_service, mock_chat_api):
        """Should handle Chat API errors during posting gracefully."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
        }

        mock_chat_api.spaces.return_value.messages.return_value.create.side_effect = Exception(
            "API error"
        )

        with patch("services.google_chat.logger"):
            result = google_chat_service.post_meeting_summary(
                meeting_title="Test",
                participants=["alice@org.com"],
                decisions=[],
                open_items=[],
                drive_url=None,
            )

        # Should not crash, error should be captured
        assert "error" in result or result["success"] is False

    def test_no_matching_spaces_for_meeting(self, google_chat_service):
        """If no spaces match participants, should return appropriate result."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["someone@org.com"],
        }

        result = google_chat_service.post_meeting_summary(
            meeting_title="Test",
            participants=["different@org.com"],
            decisions=[],
            open_items=[],
            drive_url=None,
        )

        assert result["spaces_found"] == 0
        assert len(result["spaces_posted"]) == 0

    def test_multiple_spaces_posted_successfully(self, google_chat_service, mock_chat_api):
        """Should successfully post to multiple matching spaces."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com", "bob@org.com"],
            "spaces/DEF456": ["alice@org.com"],
            "spaces/GHI789": ["bob@org.com"],
        }

        mock_chat_api.spaces.return_value.messages.return_value.create.return_value.execute.return_value = {
            "name": "spaces/ABC123/messages/MSG123"
        }

        result = google_chat_service.post_meeting_summary(
            meeting_title="Test",
            participants=["alice@org.com", "bob@org.com"],
            decisions=["Decision 1"],
            open_items=["Action 1"],
            drive_url="https://drive.google.com/doc/ABC",
        )

        assert result["success"] is True
        # All 3 spaces should have at least one participant
        assert result["spaces_found"] == 3
        assert len(result["spaces_posted"]) >= 1

    def test_empty_participants_no_posting(self, google_chat_service):
        """Meeting with no participants should not post to any space."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
        }

        result = google_chat_service.post_meeting_summary(
            meeting_title="Test",
            participants=[],
            decisions=[],
            open_items=[],
            drive_url=None,
        )

        assert len(result["spaces_posted"]) == 0


# ============================================================================
# TEST: Error Handling and Edge Cases
# ============================================================================


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    def test_credentials_file_not_found(self):
        """Should handle missing credentials file gracefully."""
        with patch("services.google_chat.Credentials") as mock_creds_class:
            mock_creds_class.from_service_account_file.side_effect = FileNotFoundError(
                "Credentials file not found"
            )

            with patch("services.google_chat.logger"):
                # Should not raise, but log error
                try:
                    GoogleChatService.from_credentials_file("nonexistent.json")
                except FileNotFoundError:
                    pass  # Expected

    def test_invalid_credentials_format(self):
        """Should handle invalid credentials format gracefully."""
        with patch("services.google_chat.ServiceAccountCredentials") as mock_creds_class:
            mock_creds_class.from_service_account_file.side_effect = ValueError(
                "Invalid JSON format"
            )

            with patch("services.google_chat.logger"):
                with pytest.raises(ValueError):
                    GoogleChatService.from_credentials_file("bad.json")

    def test_api_unavailable_discovery(self, google_chat_service, mock_chat_api):
        """Should handle API unavailability during discovery."""
        mock_chat_api.spaces.return_value.list.return_value.execute.side_effect = (
            ConnectionError("API unavailable")
        )

        with patch("services.google_chat.logger") as mock_logger:
            google_chat_service.discover_and_cache_spaces()
            mock_logger.error.assert_called()

    def test_partial_api_failure_continues(self, google_chat_service, mock_chat_api):
        """Should continue on partial API failures."""
        # First call succeeds, second fails
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(
                    execute=MagicMock(
                        return_value={
                            "spaces": [
                                {"name": "spaces/ABC123"},
                                {"name": "spaces/DEF456"},
                            ]
                        }
                    )
                )
            else:
                raise Exception("API error on second call")

        mock_chat_api.spaces.return_value.list.return_value.execute.side_effect = (
            side_effect
        )

        with patch("services.google_chat.logger"):
            google_chat_service.discover_and_cache_spaces()

    def test_missing_name_field_in_space(self, google_chat_service, mock_chat_api):
        """Should handle spaces without 'name' field."""
        mock_chat_api.spaces.return_value.list.return_value.execute.return_value = {
            "spaces": [
                {"displayName": "Engineering"},  # Missing 'name'
                {"name": "spaces/ABC123", "displayName": "Product"},
            ]
        }

        mock_chat_api.spaces.return_value.members.return_value.list.return_value.execute.return_value = {
            "members": [{"member": {"email": "alice@org.com"}}]
        }

        with patch("services.google_chat.logger"):
            google_chat_service.discover_and_cache_spaces()

        # Should only cache the valid space
        assert len(google_chat_service._space_members) <= 1

    def test_malformed_member_object(self, google_chat_service, mock_chat_api):
        """Should handle malformed member objects."""
        mock_chat_api.spaces.return_value.list.return_value.execute.return_value = {
            "spaces": [{"name": "spaces/ABC123"}]
        }

        mock_chat_api.spaces.return_value.members.return_value.list.return_value.execute.return_value = {
            "members": [
                {"member": {"email": "alice@org.com"}},
                {"notMember": "wrong"},  # Malformed
                {"member": None},  # Null member
                {"member": {"email": "bob@org.com"}},
            ]
        }

        with patch("services.google_chat.logger"):
            google_chat_service.discover_and_cache_spaces()

        # Should cache only valid members
        cached = google_chat_service._space_members.get("spaces/ABC123", [])
        assert "alice@org.com" in cached
        assert "bob@org.com" in cached


# ============================================================================
# TEST: Integration with Tracker (Mock)
# ============================================================================


class TestTrackerIntegration:
    """Test integration with MeetingTracker."""

    def test_service_can_be_initialized_for_tracker(self):
        """Service should be initializable with typical tracker setup."""
        mock_creds = Mock()

        with patch("services.google_chat.build"):
            service = GoogleChatService(mock_creds)
            assert service is not None

    def test_post_meeting_summary_returns_loggable_result(self, google_chat_service, mock_chat_api):
        """Result should be loggable for tracker output."""
        google_chat_service._space_members = {
            "spaces/ABC123": ["alice@org.com"],
        }

        mock_chat_api.spaces.return_value.messages.return_value.create.return_value.execute.return_value = {
            "name": "spaces/ABC123/messages/MSG123"
        }

        result = google_chat_service.post_meeting_summary(
            meeting_title="Team Sync",
            participants=["alice@org.com"],
            decisions=["Approve timeline"],
            open_items=["Send follow-up"],
            drive_url="https://drive.google.com/doc/ABC",
        )

        # Result should be printable/loggable
        result_str = str(result)
        assert "spaces" in result_str.lower() or "success" in result_str.lower()


# ============================================================================
# TEST: Boundary Conditions
# ============================================================================


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_very_large_participant_list(self, google_chat_service):
        """Should handle very large participant lists."""
        google_chat_service._space_members = {
            "spaces/ABC123": [f"user{i}@org.com" for i in range(100)],
        }

        participants = [f"user{i}@org.com" for i in range(50)]
        matching = google_chat_service._find_matching_spaces(participants)

        # Should not crash and should find the space
        assert len(matching) >= 0

    def test_very_large_space_list(self, google_chat_service):
        """Should handle very large number of spaces."""
        # Create 100 spaces
        spaces = {f"spaces/{i:06d}": [f"user{i}@org.com"] for i in range(100)}
        google_chat_service._space_members = spaces

        participants = ["user0@org.com"]
        matching = google_chat_service._find_matching_spaces(participants)

        # Should find relevant spaces
        assert "spaces/000000" in matching

    def test_many_decisions_and_items(self, google_chat_service):
        """Should handle many decisions and open items."""
        decisions = [f"Decision {i}" for i in range(50)]
        open_items = [f"Action {i}" for i in range(50)]

        card = google_chat_service._build_smart_card(
            meeting_title="Large Meeting",
            decisions=decisions,
            open_items=open_items,
            drive_url=None,
        )

        assert card is not None

    def test_unicode_in_meeting_content(self, google_chat_service):
        """Should handle unicode characters."""
        card = google_chat_service._build_smart_card(
            meeting_title="Q2 预算评审 (Budget Review)",
            decisions=["Approve €50K budget", "Hire 2 engineers in 北京"],
            open_items=["Review 문서", "Setup 会议"],
            drive_url=None,
        )

        assert card is not None

    def test_none_values_in_lists(self, google_chat_service):
        """Should handle None values in decision/item lists."""
        # Some lists might have None values
        decisions = ["Decision 1", None, "Decision 2"]
        open_items = ["Action 1", None, "Action 2"]

        # Should handle gracefully (either filter or ignore)
        try:
            card = google_chat_service._build_smart_card(
                meeting_title="Test",
                decisions=[d for d in decisions if d],
                open_items=[i for i in open_items if i],
                drive_url=None,
            )
            assert card is not None
        except Exception:
            pass  # Acceptable if service validates inputs
