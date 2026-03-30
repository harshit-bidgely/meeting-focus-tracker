"""Calendar Watcher — polls Google Calendar and auto-prompts users to invite the bot.

Flow:
  1. Polls Google Calendar every CALENDAR_POLL_INTERVAL seconds
  2. Detects meetings with a Google Meet link starting within AUTO_JOIN_LEAD_MINUTES
  3. Shows a macOS popup: "Meeting X is starting — invite FocusBot?"
  4. On confirmation, sends the Vexa bot into the meeting
  5. Starts the MeetingFocusTracker in a background thread
  6. Continues watching — supports multiple simultaneous meetings
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from config import Config
from services.google_calendar import GoogleCalendarService, CalendarEvent
from services.vexa_client import VexaClient

logger = logging.getLogger(__name__)


@dataclass
class WatcherState:
    """Tracks which meetings we've already handled."""
    processed_event_ids: set = field(default_factory=set)
    active_meetings: dict = field(default_factory=dict)  # meet_id → thread
    lock: threading.Lock = field(default_factory=threading.Lock)


class CalendarWatcher:
    """Watches Google Calendar and auto-launches the tracker for each meeting."""

    def __init__(self, google_creds, vexa_client: VexaClient | None = None) -> None:
        self.google_creds = google_creds
        self.calendar = GoogleCalendarService(google_creds)
        self.vexa = vexa_client or VexaClient(
            api_base=Config.VEXA_API_BASE, api_key=Config.VEXA_API_KEY
        )
        self.state = WatcherState()
        self.poll_interval = Config.CALENDAR_POLL_INTERVAL
        self.lead_minutes = Config.AUTO_JOIN_LEAD_MINUTES

    def get_actionable_events(self) -> list[CalendarEvent]:
        """Find meetings starting soon that have a Google Meet link and haven't been handled."""
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=self.lead_minutes)

        events = self._fetch_upcoming_events()
        actionable = []

        for event in events:
            # Skip if no Meet link
            if not event.meet_id:
                continue
            # Skip if already processed
            if event.event_id in self.state.processed_event_ids:
                continue
            # Skip if meeting already ended
            if event.end_time.astimezone(timezone.utc) <= now:
                continue
            # Include if meeting is in progress OR starts within the lead window
            if event.start_time.astimezone(timezone.utc) <= window_end:
                actionable.append(event)

        return actionable

    def _fetch_upcoming_events(self) -> list[CalendarEvent]:
        """Fetch upcoming events from Google Calendar."""
        try:
            now = datetime.now(timezone.utc)
            time_min = now.isoformat()
            time_max = (now + timedelta(hours=8)).isoformat()

            result = self.calendar.service.events().list(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = []
            for raw in result.get("items", []):
                parsed = self.calendar._parse_event(raw)
                if parsed:
                    events.append(parsed)
            return events
        except Exception:
            logger.exception("Failed to fetch calendar events")
            return []

    def prompt_user_to_invite_bot(self, event: CalendarEvent) -> bool:
        """Show a macOS notification prompting the user to invite FocusBot.

        Returns True if the user accepted (clicked the notification).
        For macOS, we use an AppleScript dialog that blocks until the user responds.
        """
        safe_summary = (event.summary or "Meeting").replace('"', '\\"')
        meet_url = f"https://meet.google.com/{event.meet_id}"

        # Calculate time info
        now = datetime.now(timezone.utc)
        start_utc = event.start_time.astimezone(timezone.utc)
        if start_utc <= now:
            time_info = "IN PROGRESS NOW"
        else:
            mins = int((start_utc - now).total_seconds() / 60)
            time_info = f"starts in {mins} min"

        applescript = f'''
        tell application "System Events"
            display dialog "Meeting: {safe_summary}\\n{time_info}\\n\\nJoin & invite FocusBot to track focus?\\n\\nMeet: {meet_url}" ¬
                buttons {{"Skip", "Invite FocusBot"}} ¬
                default button "Invite FocusBot" ¬
                with title "Meeting Focus Tracker" ¬
                giving up after 120
        end tell
        '''

        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True, text=True, timeout=130,
            )
            output = result.stdout.strip()
            # AppleScript returns "button returned:Invite FocusBot" on acceptance
            if "Invite FocusBot" in output:
                return True
            # User clicked Skip or dialog timed out
            return False
        except subprocess.TimeoutExpired:
            logger.warning("Bot invite prompt timed out")
            return False
        except Exception:
            logger.exception("Failed to show bot invite prompt")
            return False

    def start_bot_for_event(self, event: CalendarEvent) -> bool:
        """Send the Vexa bot into the meeting. Returns True on success."""
        try:
            self.vexa.start_bot(
                platform=Config.MEETING_PLATFORM,
                meeting_id=event.meet_id,
            )
            logger.info("Bot sent to meeting %s (%s)", event.meet_id, event.summary)
            return True
        except Exception:
            logger.exception("Failed to start bot for %s", event.meet_id)
            return False

    def notify_bot_sent(self, event: CalendarEvent) -> None:
        """Show a confirmation notification that the bot was sent."""
        safe_summary = (event.summary or "Meeting").replace('"', '\\"')
        applescript = (
            f'display notification "FocusBot is joining {safe_summary}. '
            f'Admit it in Google Meet when it appears." '
            f'with title "Meeting Focus Tracker" '
            f'subtitle "Bot Joining..." '
            f'sound name "Glass"'
        )
        try:
            subprocess.Popen(["osascript", "-e", applescript])
        except Exception:
            pass

    def handle_event(self, event: CalendarEvent) -> bool:
        """Full flow for one event: prompt → send bot → mark processed.

        Returns True if the bot was sent successfully.
        """
        logger.info(
            "Actionable event: %s (meet=%s, starts=%s)",
            event.summary, event.meet_id, event.start_time.isoformat(),
        )

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
                self.state.active_meetings[event.meet_id] = None  # thread set later
            print(f"  FocusBot sent to: {event.summary} ({event.meet_id})")
            print(f"  Admit 'FocusBot' in Google Meet when it appears")
        return success

    def _run_tracker_for_event(self, event: CalendarEvent) -> None:
        """Run a MeetingFocusTracker for a single event (called in a thread)."""
        from tracker import MeetingFocusTracker

        description = event.description or event.summary

        print(f"\n  [{event.meet_id}] Starting tracker for: {event.summary}")
        try:
            tracker = MeetingFocusTracker(
                meeting_id=event.meet_id,
                google_creds=self.google_creds,
                meeting_title=event.summary,
                attendees=event.attendees,
            )
            tracker.run(description)
        except Exception:
            logger.exception("Tracker crashed for %s", event.meet_id)
        finally:
            with self.state.lock:
                self.state.active_meetings.pop(event.meet_id, None)
            print(f"\n  [{event.meet_id}] Meeting ended: {event.summary}")

    def _cleanup_finished_threads(self) -> None:
        """Remove references to threads that have finished."""
        with self.state.lock:
            finished = [
                mid for mid, t in self.state.active_meetings.items()
                if t is not None and not t.is_alive()
            ]
            for mid in finished:
                del self.state.active_meetings[mid]

    def run(self) -> None:
        """Main watcher loop — runs forever, launching tracker threads for meetings."""
        print("\n" + "=" * 60)
        print("  MEETING FOCUS TRACKER — AUTO MODE")
        print("=" * 60)
        print(f"  Calendar : {Config.GOOGLE_CALENDAR_ID}")
        print(f"  Poll     : every {self.poll_interval}s")
        print(f"  Lead time: {self.lead_minutes} min before meeting")
        print(f"  Platform : {Config.MEETING_PLATFORM}")
        print(f"  Multi-meeting: enabled (threaded)")
        print("=" * 60)
        print("  Watching for meetings... (Ctrl+C to stop)\n")

        try:
            while True:
                self._cleanup_finished_threads()
                events = self.get_actionable_events()

                for event in events:
                    # Skip if this meeting already has an active tracker
                    with self.state.lock:
                        if event.meet_id in self.state.active_meetings:
                            continue

                    success = self.handle_event(event)
                    if not success:
                        continue

                    # Launch tracker in a background thread
                    thread = threading.Thread(
                        target=self._run_tracker_for_event,
                        args=(event,),
                        name=f"tracker-{event.meet_id}",
                        daemon=True,
                    )
                    with self.state.lock:
                        self.state.active_meetings[event.meet_id] = thread
                    thread.start()

                # Show active meetings count
                with self.state.lock:
                    active_count = len(self.state.active_meetings)
                if active_count > 0:
                    logger.debug("%d active meeting(s) being tracked", active_count)

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            with self.state.lock:
                active = list(self.state.active_meetings.keys())
            if active:
                print(f"\nWaiting for {len(active)} active meeting(s) to save...")
                for mid, t in list(self.state.active_meetings.items()):
                    if t and t.is_alive():
                        t.join(timeout=15)
            print("Stopping calendar watcher. Goodbye!")
