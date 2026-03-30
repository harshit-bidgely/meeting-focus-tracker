# Google Chat Integration Design

**Date**: 2026-03-30
**Status**: Design Approved
**Scope**: Post meeting summaries to Google Chat spaces based on meeting participants

---

## Overview

After each meeting ends, automatically post a formatted summary to Google Chat spaces where meeting participants are members. Uses the Google Chat API to discover available spaces and intelligently match participants, eliminating manual configuration.

**Success Criteria:**
- ✅ Service account authenticates to Google Chat API
- ✅ Spaces and member lists cached on startup
- ✅ Meeting participants matched to accessible spaces
- ✅ Summaries posted to matching spaces with smart card format
- ✅ Feature-flagged via `ENABLE_GOOGLE_CHAT=true/false`
- ✅ Non-blocking: failures don't break meeting workflow
- ✅ 100% backward compatible with existing integrations

---

## Architecture

### Authentication
- **Type**: Google Service Account (org-level)
- **Credentials File**: Stored at path specified by `GOOGLE_CHAT_CREDENTIALS_FILE` env var
- **Scopes Required**:
  - `https://www.googleapis.com/auth/chat.bot` - Post messages
  - `https://www.googleapis.com/auth/chat.spaces` - List spaces and members
- **Setup**: Service account must be created in Google Cloud Console and invited to target Chat spaces

### Service Class: `GoogleChatService`

**File**: `services/google_chat.py`

**Interface**:
```python
class GoogleChatService:
    def __init__(self, credentials: Credentials) -> None:
        """Initialize with service account credentials."""

    def discover_and_cache_spaces(self) -> None:
        """Query Chat API for all accessible spaces and cache members.

        Called once on startup. Queries spaces.list() and for each space,
        fetches the member list. Stores in self._space_members dict:
        {
            "spaces/ABC123": ["user1@org.com", "user2@org.com", ...],
            "spaces/DEF456": ["user3@org.com", "user4@org.com", ...],
        }
        """

    def post_meeting_summary(
        self,
        meeting_title: str,
        participants: list[str],
        decisions: list[str],
        open_items: list[str],
        drive_url: str | None,
    ) -> dict:
        """Post meeting summary to spaces where participants are members.

        Args:
            meeting_title: Title of the meeting
            participants: List of attendee email addresses
            decisions: List of key decisions made
            open_items: List of action items/open items
            drive_url: URL to full meeting notes in Google Drive (optional)

        Returns:
            {
                "success": bool,
                "spaces_posted": list[str],  # Space IDs where posted
                "spaces_found": int,         # Total matching spaces
                "error": str | None          # Error message if failed
            }
        """
```

**Internal Methods**:
- `_build_smart_card(...)` → Formats Google Chat smart card message
- `_find_matching_spaces(participants: list[str]) -> list[str]` → Returns space IDs where >1 participant is a member

### Message Format

**Smart Card Structure** (Google Chat API format):
```
[Card]
Title: "📋 Meeting: {title}"
Sections:
  1. Key Decisions
     - Bullet list of decisions

  2. Action Items
     - Numbered list with owners if available

  3. Footer
     - Meeting date/time
     - "View full summary" button → link to Google Drive doc
```

**Plain Text Fallback** (if smart cards unavailable):
```
📋 Meeting: {title}

Key Decisions:
• Decision 1
• Decision 2

Action Items:
1. Action 1
2. Action 2

View full summary: {drive_url}
```

### Integration with Tracker

**File**: `tracker.py`
**Method**: `_save_to_memory()` (line ~440-503)

**Addition**:
```python
# After Google Drive and Gmail exports (feature-flagged)
if self.config.get("ENABLE_GOOGLE_CHAT"):
    chat_result = self._export_to_google_chat()
    if chat_result:
        print(f"✓ Posted to {chat_result['spaces_posted']} Chat spaces")
```

**New Method in MeetingTracker**:
```python
def _export_to_google_chat(self) -> dict:
    """Export meeting summary to Google Chat spaces."""
    # Extract data
    meeting_title = self.meeting_data.get("title", "Meeting")
    participants = self.meeting_data.get("attendees", [])
    decisions = self.meeting_data.get("decisions", [])
    open_items = self.meeting_data.get("open_items", [])
    drive_url = self.meeting_data.get("drive_url")

    # Post to Chat
    result = self.chat_service.post_meeting_summary(
        meeting_title, participants, decisions, open_items, drive_url
    )

    # Store result in summary data
    self.meeting_data["chat_export"] = result
    return result
```

### Startup Initialization

**File**: `tracker.py` (or main entry point)

On startup, if `ENABLE_GOOGLE_CHAT=true`:
```python
if config.get("ENABLE_GOOGLE_CHAT"):
    chat_service = GoogleChatService(credentials)
    chat_service.discover_and_cache_spaces()
    # Service is then passed to MeetingTracker instance
```

---

## Configuration

### Environment Variables

Add to `.env`:
```env
# Google Chat Integration
ENABLE_GOOGLE_CHAT=true
GOOGLE_CHAT_CREDENTIALS_FILE=chat_credentials.json
```

### Required Setup

1. **Create Service Account** (Google Cloud Console)
   - Project: Same as existing Google integrations
   - Service account with Chat API access
   - Download JSON key file

2. **Invite Service Account to Spaces**
   - Add service account email to any Google Chat spaces where you want summaries posted
   - Must be a member to post messages

3. **Store Credentials**
   - Place JSON key file at path specified by `GOOGLE_CHAT_CREDENTIALS_FILE`
   - (Typically: `./chat_credentials.json`)

---

## Error Handling

### Graceful Degradation

- If Chat API is unavailable: log warning, continue (non-blocking)
- If no spaces found for meeting: skip Chat posting, log info
- If space posting fails: log error, continue to next space
- If credentials missing: skip Chat entirely if `ENABLE_GOOGLE_CHAT=true`

### Logging

```python
logger.info("Found %d spaces for %d participants", len(matching_spaces), len(participants))
logger.warning("Failed to post to space %s: %s", space_id, error)
logger.error("Chat API unavailable: %s", error)
```

---

## Testing Strategy

### Unit Tests: `tests/test_google_chat.py`

**Test Coverage** (~20-25 tests):

1. **Initialization**
   - Service account credentials loaded correctly
   - Chat API client built

2. **Space Discovery**
   - `discover_and_cache_spaces()` queries API correctly
   - Member lists cached properly
   - Handles empty space list
   - Handles API errors gracefully

3. **Matching Logic**
   - Single participant matches space with that member
   - Multiple participants find spaces where >1 are members
   - No matches returns empty list
   - Case-insensitive email matching
   - Handles invalid email formats

4. **Message Posting**
   - Correctly formats smart card structure
   - Posts to matching spaces
   - Skips spaces with no matching participants
   - Returns success dict with correct fields
   - Handles API errors during posting

5. **Message Format**
   - Includes title, decisions, open items
   - Handles empty decisions list
   - Handles empty open items list
   - Includes Drive link when available
   - Omits Drive link when None

6. **Integration**
   - `_export_to_google_chat()` in tracker calls service correctly
   - Results stored in meeting data
   - Feature flag respected

### Mocking Strategy

- Mock `googleapiclient.discovery.build()` to return mock Chat API client
- Mock API responses for `spaces.list()`, `spaces.members.list()`, `spaces.messages.create()`
- Mock credentials loading via `google.oauth2.service_account.Credentials.from_service_account_file()`

---

## Data Flow

```
Meeting Ends
    ↓
[_save_to_memory() in tracker.py]
    ↓
Check: ENABLE_GOOGLE_CHAT == true?
    ├─ No → Skip
    └─ Yes ↓

Extract meeting data:
  - title, participants, decisions, open_items, drive_url
    ↓
[GoogleChatService.post_meeting_summary()]
    ↓
Find matching spaces (participants ∩ space_members)
    ↓
For each matching space:
  - Build smart card message
  - Post via Chat API
  - Log result
    ↓
Return posting results
    ↓
Store in meeting_data["chat_export"]
    ↓
Display to user: "✓ Posted to X Chat spaces"
```

---

## Backward Compatibility

✅ **100% Backward Compatible**
- Feature is entirely optional via `ENABLE_GOOGLE_CHAT` flag
- Existing workflows unaffected
- No changes to core tracker logic
- Graceful degradation if Chat API unavailable
- No new required dependencies beyond existing Google API client

---

## Performance Impact

### API Calls
- **Startup**: 1 call to `spaces.list()` + N calls to `spaces.members.list()` (cached)
- **Per Meeting**: N calls to `spaces.messages.create()` (N = number of matching spaces)
- **Subsequent Meetings**: No new space discovery calls (uses cache)

### Memory
- Space cache: ~1-2KB per space (ID + member list)
- Typical org: 20-50 spaces → ~50-100KB

### Latency
- Startup discovery: ~2-5 seconds (depends on # of spaces)
- Per-meeting posting: Async, non-blocking
- User doesn't wait for Chat operations

---

## Files to Create/Modify

### New Files
- `services/google_chat.py` (150-200 lines)
- `tests/test_google_chat.py` (200-250 lines)

### Modified Files
- `tracker.py` (add method `_export_to_google_chat()`, add Chat service initialization)
- `.env` (add `ENABLE_GOOGLE_CHAT`, `GOOGLE_CHAT_CREDENTIALS_FILE`)

### No Changes Needed
- Existing Google Drive service
- Existing Gmail service
- Existing metrics/validator services
- Core tracker logic

---

## Deployment Checklist

- [ ] Google Chat service account created in Google Cloud
- [ ] Service account JSON key downloaded
- [ ] Service account invited to target Chat spaces
- [ ] `GOOGLE_CHAT_CREDENTIALS_FILE` path configured in `.env`
- [ ] `ENABLE_GOOGLE_CHAT=true` set in `.env` (or false to disable)
- [ ] Code implemented and tested
- [ ] All 20+ new tests passing
- [ ] Integration with tracker verified
- [ ] Error handling verified (Chat API unavailable scenario)
- [ ] Documentation updated
- [ ] Ready for production deployment

---

## Success Metrics

After implementation:
- Meeting summaries automatically appear in Google Chat spaces within seconds of meeting end
- All meeting participants can see relevant summaries in their team spaces
- Zero impact on meeting workflow (async, non-blocking)
- All existing tests still passing
- 202+ total tests passing (including new Chat tests)

---

## Future Enhancements (Out of Scope)

- Post to Slack as well (similar pattern)
- Threaded conversations (reply to summary with questions)
- Rich formatting (embeds, file attachments)
- Smart filtering (only post to spaces with 50%+ participant overlap)
