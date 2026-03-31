#!/usr/bin/env python3
"""Entry point for the Meeting Focus Tracker.

Usage:
    python3 main.py              # Manual mode — track a single meeting
    python3 main.py --auto       # Auto mode  — watch calendar, prompt to invite bot
"""

from __future__ import annotations

import logging
import sys

from config import Config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    auto_mode = "--auto" in sys.argv

    if auto_mode:
        _run_auto_mode()
    else:
        _run_manual_mode()


# ──────────────────────────────────────────────────────────────
# Auto mode — watches calendar, prompts user, auto-launches bot
# ──────────────────────────────────────────────────────────────

def _run_auto_mode() -> None:
    """Watch Google Calendar and auto-invite bot to meetings."""
    # Auto mode requires Google Calendar
    missing = []
    if not Config.LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if not Config.VEXA_API_KEY:
        missing.append("VEXA_API_KEY")
    if missing:
        print(f"Missing required config: {', '.join(missing)}")
        sys.exit(1)

    google_creds = _setup_google_auth()
    if not google_creds:
        print("Google authentication is required for auto mode.")
        print("Set GOOGLE_CREDENTIALS_FILE in .env and try again.")
        sys.exit(1)

    from services.calendar_watcher import CalendarWatcher
    watcher = CalendarWatcher(google_creds=google_creds)
    watcher.run()


# ──────────────────────────────────────────────────────────────
# Manual mode — original single-meeting flow
# ──────────────────────────────────────────────────────────────

def _run_manual_mode() -> None:
    """Run the tracker for a single meeting (original behavior)."""
    from tracker import MeetingFocusTracker

    missing = Config.validate()
    if missing:
        print(f"Missing required config: {', '.join(missing)}")
        print("Set them in .env or as environment variables.")
        sys.exit(1)

    # Google Workspace setup
    google_creds = None
    calendar_event = None
    if Config.google_enabled():
        google_creds = _setup_google_auth()
        if not google_creds:
            print("Google authentication failed. Continuing without G Suite features.")

    # Try to auto-fetch meeting from Google Calendar
    description = Config.CALENDAR_DESCRIPTION
    meeting_id = Config.MEETING_ID
    attendees: list[str] = []

    if Config.ENABLE_GOOGLE_CALENDAR and google_creds:
        calendar_event = _fetch_from_calendar(google_creds)
        if calendar_event:
            if not description.strip():
                description = calendar_event.description
                print(f"  Calendar agenda loaded: {calendar_event.summary}")
            if not meeting_id and calendar_event.meet_id:
                meeting_id = calendar_event.meet_id
                print(f"  Meet ID from calendar: {meeting_id}")
            attendees = calendar_event.attendees

    # Fallback: manual input
    if not description.strip():
        print("No CALENDAR_DESCRIPTION found in .env (and no Google Calendar event).")
        print("Paste the calendar event description below (empty line to finish):")
        lines: list[str] = []
        try:
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
        except EOFError:
            pass
        description = "\n".join(lines)

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

    if not meeting_id:
        print("No MEETING_ID found (and none from Google Calendar). Exiting.")
        sys.exit(1)

    meeting_title = ""
    if calendar_event:
        meeting_title = calendar_event.summary

    # Set Config values for tracker initialization
    Config.MEETING_ID = meeting_id

    # Temporarily store Google credentials for tracker to use (if supported)
    # The tracker can access these through module-level storage if needed
    tracker = MeetingFocusTracker()
    tracker.run(description)


# ──────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────

def _setup_google_auth():
    """Authenticate with Google and return credentials."""
    try:
        from services.google_auth import get_google_credentials
        creds = get_google_credentials(
            credentials_file=Config.GOOGLE_CREDENTIALS_FILE,
            token_file=Config.GOOGLE_TOKEN_FILE,
        )
        print("  Google authenticated successfully")
        return creds
    except FileNotFoundError as e:
        print(f"  {e}")
        return None
    except Exception as e:
        logging.getLogger(__name__).exception("Google auth failed")
        print(f"  Google auth error: {e}")
        return None


def _fetch_from_calendar(google_creds):
    """Fetch the current or next meeting from Google Calendar."""
    try:
        from services.google_calendar import GoogleCalendarService
        cal = GoogleCalendarService(google_creds)
        event = cal.get_current_or_next_event(calendar_id=Config.GOOGLE_CALENDAR_ID)
        if event:
            print(f"\n  Found calendar event: {event.summary}")
            if event.meet_id:
                print(f"  Google Meet: {event.meet_id}")
            if event.attendees:
                print(f"  Attendees: {len(event.attendees)}")
            return event
        else:
            print("  No upcoming calendar events found.")
            return None
    except Exception as e:
        logging.getLogger(__name__).exception("Calendar fetch failed")
        print(f"  Calendar error: {e}")
        return None


if __name__ == "__main__":
    main()
