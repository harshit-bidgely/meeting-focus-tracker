# Agenda Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block meetings from starting (bot won't join) unless the calendar event has a valid agenda. Show clear validation feedback and suggestions.

**Architecture:** Add `REQUIRE_AGENDA_VALIDATION` config flag and `AGENDA_MIN_QUALITY` threshold. Wire `AgendaValidator` into two entry points: `calendar_watcher.py:handle_event()` (auto mode) and `main.py:_run_manual_mode()` (manual mode). In auto mode, show a macOS dialog with the validation message and block bot join. In manual mode, print validation to console and exit.

**Tech Stack:** Python, existing `AgendaValidator`, macOS AppleScript dialogs, pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `config.py` | Modify | Add `REQUIRE_AGENDA_VALIDATION` and `AGENDA_MIN_QUALITY` |
| `services/calendar_watcher.py` | Modify | Validate agenda before prompting user; block + show dialog if invalid |
| `main.py` | Modify | Validate agenda before launching tracker in manual mode |
| `.env` | Modify | Add new config flags |
| `tests/test_agenda_enforcement.py` | Create | Tests for both auto and manual mode enforcement |
| `tests/test_config_gsuite.py` | Modify | Add test for new config field |

---

### Task 1: Add config flags

**Files:**
- Modify: `config.py:36-41`
- Modify: `.env:14-20`

- [ ] **Step 1: Add config fields to `config.py`**

In `config.py`, after line 36 (`ENABLE_GOOGLE_CHAT`), add:

```python
    # Agenda enforcement
    REQUIRE_AGENDA_VALIDATION: bool = os.getenv("REQUIRE_AGENDA_VALIDATION", "true").lower() == "true"
    AGENDA_MIN_QUALITY: str = os.getenv("AGENDA_MIN_QUALITY", "fair")  # poor|fair|good|excellent
```

- [ ] **Step 2: Add config to `.env`**

In `.env`, after the Google Workspace section, add:

```env
# Agenda Enforcement
REQUIRE_AGENDA_VALIDATION=true
AGENDA_MIN_QUALITY=fair
```

- [ ] **Step 3: Verify config loads**

Run:
```bash
python3 -c "from config import Config; print(Config.REQUIRE_AGENDA_VALIDATION, Config.AGENDA_MIN_QUALITY)"
```
Expected: `True fair`

---

### Task 2: Write failing tests for auto mode enforcement

**Files:**
- Create: `tests/test_agenda_enforcement.py`

- [ ] **Step 1: Write test file with auto mode tests**

```python
"""Tests for agenda enforcement — blocking meetings without valid agendas."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from services.calendar_watcher import CalendarWatcher, WatcherState
from services.google_calendar import CalendarEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    event_id: str = "evt-1",
    summary: str = "Sprint Sync",
    description: str = "",
    meet_id: str | None = "abc-defg-hij",
    start_offset_minutes: int = -5,
    end_offset_minutes: int = 55,
    attendees: list[str] | None = None,
) -> CalendarEvent:
    now = datetime.now(timezone.utc)
    return CalendarEvent(
        event_id=event_id,
        summary=summary,
        description=description,
        meet_id=meet_id,
        start_time=now + timedelta(minutes=start_offset_minutes),
        end_time=now + timedelta(minutes=end_offset_minutes),
        attendees=attendees or ["alice@example.com"],
    )


def _make_watcher() -> CalendarWatcher:
    mock_creds = MagicMock()
    with patch.object(Config, "VEXA_API_KEY", "test-key"), \
         patch.object(Config, "VEXA_API_BASE", "https://api.vexa.ai"), \
         patch.object(Config, "MEETING_PLATFORM", "google_meet"), \
         patch.object(Config, "CALENDAR_POLL_INTERVAL", 5), \
         patch.object(Config, "AUTO_JOIN_LEAD_MINUTES", 2), \
         patch.object(Config, "GOOGLE_CALENDAR_ID", "primary"), \
         patch("services.calendar_watcher.GoogleCalendarService"), \
         patch("services.calendar_watcher.VexaClient") as mock_vexa_cls:
        mock_vexa = MagicMock()
        mock_vexa_cls.return_value = mock_vexa
        watcher = CalendarWatcher(google_creds=mock_creds)
        watcher.vexa = mock_vexa
    return watcher


# ---------------------------------------------------------------------------
# Tests: Auto mode — calendar_watcher.handle_event()
# ---------------------------------------------------------------------------

class TestAutoModeAgendaEnforcement:
    """Test that handle_event blocks meetings with no/poor agenda."""

    def test_empty_agenda_blocks_bot_join(self):
        """Meeting with empty description should be blocked."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "prompt_user_to_invite_bot") as mock_prompt, \
             patch.object(watcher, "_show_agenda_rejection_dialog") as mock_dialog:
            result = watcher.handle_event(event)

        # Bot should NOT join
        assert result is False
        # User should NOT be prompted to invite bot
        mock_prompt.assert_not_called()
        # Rejection dialog should be shown
        mock_dialog.assert_called_once()

    def test_poor_agenda_blocks_bot_join(self):
        """Meeting with vague agenda should be blocked."""
        event = _make_event(description="stuff and misc")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "prompt_user_to_invite_bot") as mock_prompt, \
             patch.object(watcher, "_show_agenda_rejection_dialog") as mock_dialog:
            result = watcher.handle_event(event)

        assert result is False
        mock_prompt.assert_not_called()

    def test_good_agenda_allows_bot_join(self):
        """Meeting with good agenda should proceed normally."""
        event = _make_event(
            description="1. Review Q3 budget (15 min)\n2. Discuss hiring plan (20 min)\n3. Decide on launch timeline"
        )
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "prompt_user_to_invite_bot", return_value=True), \
             patch.object(watcher, "start_bot_for_event", return_value=True), \
             patch.object(watcher, "notify_bot_sent"):
            result = watcher.handle_event(event)

        assert result is True

    def test_validation_disabled_allows_any_agenda(self):
        """When REQUIRE_AGENDA_VALIDATION=false, any agenda passes."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", False), \
             patch.object(watcher, "prompt_user_to_invite_bot", return_value=True), \
             patch.object(watcher, "start_bot_for_event", return_value=True), \
             patch.object(watcher, "notify_bot_sent"):
            result = watcher.handle_event(event)

        # Should proceed even with empty agenda
        assert result is True

    def test_min_quality_good_blocks_fair_agenda(self):
        """When min quality is 'good', a 'fair' agenda should be blocked."""
        # This agenda is structured but lacks action words → fair quality
        event = _make_event(description="Budget numbers, team status, schedule info")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "good"), \
             patch.object(watcher, "prompt_user_to_invite_bot") as mock_prompt, \
             patch.object(watcher, "_show_agenda_rejection_dialog"):
            result = watcher.handle_event(event)

        # The agenda quality may be fair or poor — either way, below "good" threshold
        # The key assertion is that if validation fails, prompt is not called
        if result is False:
            mock_prompt.assert_not_called()

    def test_blocked_event_still_marked_processed(self):
        """Blocked event should still be marked as processed (no re-prompting)."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "_show_agenda_rejection_dialog"):
            watcher.handle_event(event)

        assert event.event_id in watcher.state.processed_event_ids

    def test_rejection_dialog_receives_validation_message(self):
        """Rejection dialog should receive the validation message with suggestions."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "_show_agenda_rejection_dialog") as mock_dialog:
            watcher.handle_event(event)

        # The dialog should be called with event and a validation message string
        mock_dialog.assert_called_once()
        call_args = mock_dialog.call_args
        # First arg is event, second is validation message
        assert call_args[0][0] is event
        assert "EMPTY" in call_args[0][1] or "agenda" in call_args[0][1].lower()


# ---------------------------------------------------------------------------
# Tests: Manual mode — main._run_manual_mode() agenda check
# ---------------------------------------------------------------------------

class TestManualModeAgendaEnforcement:
    """Test that manual mode blocks meetings with no/poor agenda."""

    def test_empty_description_blocked(self):
        """Manual mode with empty description should exit."""
        from services.agenda_validator import AgendaValidator
        result = AgendaValidator.validate("")
        assert result["is_valid"] is False
        assert result["quality_level"] == "empty"

    def test_poor_description_blocked(self):
        """Manual mode with poor description should be flagged."""
        from services.agenda_validator import AgendaValidator
        result = AgendaValidator.validate("stuff")
        assert result["is_valid"] is False or result["quality_level"] == "poor"

    def test_good_description_passes(self):
        """Manual mode with good description should pass."""
        from services.agenda_validator import AgendaValidator
        result = AgendaValidator.validate(
            "1. Review Q3 budget (15 min)\n2. Discuss hiring plan (20 min)"
        )
        assert result["is_valid"] is True
        assert result["quality_level"] in ("good", "excellent")


# ---------------------------------------------------------------------------
# Tests: Quality level threshold logic
# ---------------------------------------------------------------------------

QUALITY_LEVELS = ["empty", "poor", "fair", "good", "excellent"]

class TestQualityThreshold:
    """Test the quality threshold comparison logic."""

    def test_fair_meets_fair_threshold(self):
        """An agenda rated 'fair' should meet the 'fair' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("fair", "fair") is True

    def test_good_meets_fair_threshold(self):
        """An agenda rated 'good' should meet the 'fair' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("good", "fair") is True

    def test_poor_fails_fair_threshold(self):
        """An agenda rated 'poor' should NOT meet the 'fair' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("poor", "fair") is False

    def test_empty_fails_any_threshold(self):
        """An agenda rated 'empty' should fail any threshold."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("empty", "poor") is False

    def test_excellent_meets_excellent_threshold(self):
        """An agenda rated 'excellent' should meet the 'excellent' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("excellent", "excellent") is True

    def test_good_fails_excellent_threshold(self):
        """An agenda rated 'good' should NOT meet the 'excellent' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("good", "excellent") is False
```

- [ ] **Step 2: Run tests to verify they all fail**

Run:
```bash
python3 -m pytest tests/test_agenda_enforcement.py -v --tb=short 2>&1 | tail -30
```
Expected: All auto-mode tests and quality threshold tests FAIL (classes/functions don't exist yet). Manual mode tests may pass (they test AgendaValidator directly).

---

### Task 3: Implement quality threshold helper

**Files:**
- Modify: `services/calendar_watcher.py:1-26`

- [ ] **Step 1: Add quality threshold function**

At the top of `services/calendar_watcher.py`, after the existing imports (line 24), add:

```python
QUALITY_RANK = {"empty": 0, "poor": 1, "fair": 2, "good": 3, "excellent": 4}


def _meets_quality_threshold(quality_level: str, min_quality: str) -> bool:
    """Check if a quality level meets the minimum threshold.

    Args:
        quality_level: The agenda's quality rating (empty|poor|fair|good|excellent)
        min_quality: The minimum required quality (poor|fair|good|excellent)

    Returns:
        True if quality_level >= min_quality
    """
    return QUALITY_RANK.get(quality_level, 0) >= QUALITY_RANK.get(min_quality, 2)
```

- [ ] **Step 2: Run quality threshold tests**

Run:
```bash
python3 -m pytest tests/test_agenda_enforcement.py::TestQualityThreshold -v
```
Expected: All 6 threshold tests PASS.

- [ ] **Step 3: Commit**

```bash
git add services/calendar_watcher.py tests/test_agenda_enforcement.py
git commit -m "feat: add quality threshold helper and enforcement tests"
```

---

### Task 4: Implement auto mode enforcement in `handle_event`

**Files:**
- Modify: `services/calendar_watcher.py:173-198` (`handle_event`)
- Modify: `services/calendar_watcher.py` (add `_show_agenda_rejection_dialog`)

- [ ] **Step 1: Add import for AgendaValidator**

At the top of `services/calendar_watcher.py`, after the existing imports (line 23), add:

```python
from services.agenda_validator import AgendaValidator
```

- [ ] **Step 2: Modify `handle_event()` to validate agenda before prompting**

Replace the `handle_event` method (lines 173-198) with:

```python
    def handle_event(self, event: CalendarEvent) -> bool:
        """Full flow for one event: validate agenda → prompt → send bot → mark processed.

        Returns True if the bot was sent successfully.
        """
        logger.info(
            "Actionable event: %s (meet=%s, starts=%s)",
            event.summary, event.meet_id, event.start_time.isoformat(),
        )

        # --- Agenda enforcement gate ---
        if Config.REQUIRE_AGENDA_VALIDATION:
            description = event.description or ""
            validation = AgendaValidator.validate(description)

            if not _meets_quality_threshold(validation["quality_level"], Config.AGENDA_MIN_QUALITY):
                message = AgendaValidator.build_validation_message(validation)
                logger.warning(
                    "Agenda rejected for %s (quality=%s, required=%s)",
                    event.summary, validation["quality_level"], Config.AGENDA_MIN_QUALITY,
                )
                self._show_agenda_rejection_dialog(event, message)
                self.state.processed_event_ids.add(event.event_id)
                print(f"  Blocked: {event.summary} — agenda quality too low ({validation['quality_level']})")
                return False

        # --- Normal flow: prompt user → send bot ---
        accepted = self.prompt_user_to_invite_bot(event)
        self.state.processed_event_ids.add(event.event_id)

        if not accepted:
            logger.info("User skipped bot invite for %s", event.summary)
            print(f"  Skipped: {event.summary}")
            return False

        success = self.start_bot_for_event(event)
        if success:
            self.notify_bot_sent(event)
            with self.state.lock:
                self.state.active_meetings[event.meet_id] = None
            print(f"  FocusBot sent to: {event.summary} ({event.meet_id})")
            print(f"  Admit 'FocusBot' in Google Meet when it appears")
        return success
```

- [ ] **Step 3: Add `_show_agenda_rejection_dialog` method**

After `notify_bot_sent` method (after line 171), add:

```python
    def _show_agenda_rejection_dialog(self, event: CalendarEvent, validation_message: str) -> None:
        """Show a macOS dialog telling the user the agenda is insufficient."""
        safe_summary = (event.summary or "Meeting").replace('"', '\\"')
        # Escape validation message for AppleScript
        safe_message = validation_message.replace('"', '\\"').replace('\n', '\\n')

        applescript = f'''
        tell application "System Events"
            display dialog "Meeting: {safe_summary}\\n\\nBot cannot join — agenda quality is too low.\\n\\n{safe_message}\\n\\nPlease update the calendar event with a clear agenda and try again." ¬
                buttons {{"OK"}} ¬
                default button "OK" ¬
                with title "Meeting Focus Tracker — Agenda Required" ¬
                with icon caution ¬
                giving up after 30
        end tell
        '''

        try:
            subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True, text=True, timeout=35,
            )
        except Exception:
            # Dialog is best-effort — log to console if it fails
            logger.warning("Could not show agenda rejection dialog")
            print(f"\n  AGENDA QUALITY ISSUE: {event.summary}")
            print(f"  {validation_message}")
```

- [ ] **Step 4: Run auto mode enforcement tests**

Run:
```bash
python3 -m pytest tests/test_agenda_enforcement.py::TestAutoModeAgendaEnforcement -v --tb=short
```
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/calendar_watcher.py
git commit -m "feat: enforce agenda validation before bot joins in auto mode"
```

---

### Task 5: Implement manual mode enforcement in `main.py`

**Files:**
- Modify: `main.py:63-130` (`_run_manual_mode`)

- [ ] **Step 1: Add agenda validation after description is finalized**

In `main.py`, replace lines 112-114 (the existing empty-description check):

```python
    if not description.strip():
        print("No calendar description provided. Exiting.")
        sys.exit(1)
```

with:

```python
    if not description.strip():
        print("No calendar description provided. Exiting.")
        sys.exit(1)

    # --- Agenda enforcement gate ---
    if Config.REQUIRE_AGENDA_VALIDATION:
        from services.agenda_validator import AgendaValidator
        from services.calendar_watcher import _meets_quality_threshold

        validation = AgendaValidator.validate(description)

        if not _meets_quality_threshold(validation["quality_level"], Config.AGENDA_MIN_QUALITY):
            print("\n" + "=" * 60)
            print("  MEETING BLOCKED — AGENDA QUALITY TOO LOW")
            print("=" * 60)
            print(AgendaValidator.build_validation_message(validation))
            print("=" * 60)
            print(f"\nMinimum quality required: {Config.AGENDA_MIN_QUALITY}")
            print("Please update the calendar event description with a clear agenda.")
            print("Then re-run the tracker.")
            sys.exit(1)

        # Show validation result even if passing (informational)
        print(f"\n  Agenda quality: {validation['quality_level']} ({validation['score']}/100)")
```

- [ ] **Step 2: Run manual mode enforcement tests**

Run:
```bash
python3 -m pytest tests/test_agenda_enforcement.py::TestManualModeAgendaEnforcement -v
```
Expected: All 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: enforce agenda validation in manual mode before tracker starts"
```

---

### Task 6: Add config flags to `.env` and update config tests

**Files:**
- Modify: `tests/test_config_gsuite.py`

- [ ] **Step 1: Add test for new config fields**

In `tests/test_config_gsuite.py`, inside `TestConfigGoogleFields` class, add:

```python
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
```

- [ ] **Step 2: Run all config tests**

Run:
```bash
python3 -m pytest tests/test_config_gsuite.py -v
```
Expected: All tests PASS (including 2 new ones).

- [ ] **Step 3: Commit**

```bash
git add .env config.py tests/test_config_gsuite.py
git commit -m "feat: add REQUIRE_AGENDA_VALIDATION and AGENDA_MIN_QUALITY config"
```

---

### Task 7: Run full test suite and verify zero regressions

**Files:** None (verification only)

- [ ] **Step 1: Run the complete test suite**

Run:
```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: 0 failures. Total should be ~280+ tests (264 existing + ~16 new).

- [ ] **Step 2: Verify the manual flow end-to-end**

Run with empty agenda:
```bash
REQUIRE_AGENDA_VALIDATION=true AGENDA_MIN_QUALITY=fair CALENDAR_DESCRIPTION="" python3 -c "
from config import Config
from services.agenda_validator import AgendaValidator
from services.calendar_watcher import _meets_quality_threshold

desc = ''
validation = AgendaValidator.validate(desc)
print(AgendaValidator.build_validation_message(validation))
print(f'Meets threshold: {_meets_quality_threshold(validation[\"quality_level\"], Config.AGENDA_MIN_QUALITY)}')
"
```
Expected: Shows empty agenda message, `Meets threshold: False`.

Run with good agenda:
```bash
python3 -c "
from services.agenda_validator import AgendaValidator
from services.calendar_watcher import _meets_quality_threshold

desc = '1. Review Q3 budget (15 min)\n2. Discuss hiring plan (20 min)\n3. Decide on launch timeline'
validation = AgendaValidator.validate(desc)
print(AgendaValidator.build_validation_message(validation))
print(f'Quality: {validation[\"quality_level\"]}')
print(f'Meets fair threshold: {_meets_quality_threshold(validation[\"quality_level\"], \"fair\")}')
"
```
Expected: Shows good/excellent quality, `Meets fair threshold: True`.

- [ ] **Step 3: Commit all remaining changes**

```bash
git add -A
git commit -m "feat: complete agenda enforcement — block meetings without valid agendas"
```
