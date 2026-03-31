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

from services.agenda_validator import AgendaValidator

QUALITY_RANK = {"empty": 0, "poor": 1, "fair": 2, "good": 3, "excellent": 4}


def _meets_quality_threshold(quality_level: str, min_quality: str) -> bool:
    """Check if a quality level meets the minimum threshold."""
    return QUALITY_RANK.get(quality_level, 0) >= QUALITY_RANK.get(min_quality, 2)


@dataclass
class WatcherState:
    """Tracks which meetings we've already handled."""
    processed_event_ids: set = field(default_factory=set)
    active_meetings: dict = field(default_factory=dict)  # meet_id → thread
    notified_events: dict = field(default_factory=dict)  # event_id → {"notified_at": datetime, "quality": str}
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
            # Skip if already fully processed (bot joined or user skipped)
            if event.event_id in self.state.processed_event_ids:
                continue
            # Skip if meeting already ended
            if event.end_time.astimezone(timezone.utc) <= now:
                continue
            # Include if meeting is in progress OR starts within the lead window
            # Also include notified events (waiting for agenda update) for re-check
            is_notified = event.event_id in self.state.notified_events
            if is_notified or event.start_time.astimezone(timezone.utc) <= window_end:
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

    def _send_agenda_required_email(self, event: CalendarEvent, validation: dict) -> bool:
        """Send an email to the meeting organizer requesting they add an agenda.

        Falls back to attendees if organizer email is not available.
        Returns True if email sent successfully.
        """
        # Determine recipients — organizer first, fall back to attendees
        recipients = []
        if event.organizer_email:
            recipients = [event.organizer_email]
        elif event.attendees:
            recipients = event.attendees[:1]  # Just the first attendee as fallback

        if not recipients:
            logger.warning("No recipients for agenda-required email for %s", event.summary)
            return False

        try:
            import base64
            from email.mime.text import MIMEText
            from googleapiclient.discovery import build

            gmail = build("gmail", "v1", credentials=self.google_creds)

            subject = f"Action Required: Add agenda to \"{event.summary}\""
            body = self._build_agenda_required_email(event, validation)

            message = MIMEText(body, "html")
            message["Subject"] = subject
            message["To"] = ", ".join(recipients)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            gmail.users().messages().send(
                userId="me",
                body={"raw": raw},
            ).execute()

            logger.info(
                "Agenda-required email sent to %s for meeting %s",
                recipients, event.summary,
            )
            return True

        except Exception:
            logger.exception("Failed to send agenda-required email for %s", event.summary)
            return False

    @staticmethod
    def _build_agenda_required_email(event: CalendarEvent, validation: dict) -> str:
        """Build HTML email body requesting the organizer add an agenda."""
        issues_html = ""
        if validation.get("issues"):
            items = "".join(f"<li>{issue}</li>" for issue in validation["issues"])
            issues_html = f"<h3>Issues Found</h3><ul style='color: #c62828;'>{items}</ul>"

        suggestions_html = ""
        if validation.get("suggestions"):
            items = "".join(f"<li>{s}</li>" for s in validation["suggestions"])
            suggestions_html = f"<h3>Suggestions</h3><ul style='color: #2e7d32;'>{items}</ul>"

        quality = validation.get("quality_level", "unknown").upper()
        score = validation.get("score", 0)

        # Google Calendar edit link
        edit_url = f"https://calendar.google.com/calendar/r/eventedit/{event.event_id}" if event.event_id else ""
        edit_link = f'<a href="{edit_url}" style="color: #1a73e8;">Edit this event in Google Calendar</a>' if edit_url else ""

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #fce4ec; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <h2 style="color: #c62828; margin: 0;">Agenda Required for Your Meeting</h2>
            </div>

            <p>Your meeting <strong>"{event.summary}"</strong> does not have a sufficient agenda.</p>
            <p>The Meeting Focus Tracker bot cannot join until a clear agenda is added to the calendar event description.</p>

            <div style="background: #fff3e0; padding: 12px; border-radius: 6px; margin: 16px 0;">
                <strong>Agenda Quality:</strong> {quality} ({score}/100)
            </div>

            {issues_html}
            {suggestions_html}

            <h3>Example Agenda Format</h3>
            <div style="background: #e8f5e9; padding: 12px; border-radius: 6px; font-family: monospace;">
                1. Q3 Budget Review (15 min)<br>
                2. Team Headcount Planning (20 min)<br>
                3. Timeline &amp; Next Steps (10 min)<br>
                4. Q&amp;A (5 min)
            </div>

            <div style="margin: 20px 0; padding: 16px; background: #e3f2fd; border-radius: 8px; text-align: center;">
                <p style="margin: 0 0 8px 0;"><strong>Update your agenda and the bot will automatically join.</strong></p>
                <p style="margin: 0;">{edit_link}</p>
            </div>

            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #999; font-size: 11px;">
                This notification was sent by Meeting Focus Tracker.
                The meeting will be re-checked every {Config.CALENDAR_POLL_INTERVAL} seconds.
            </p>
        </div>
        """

    def _show_agenda_rejection_dialog(self, event: CalendarEvent, validation_message: str) -> None:
        """Show a macOS dialog telling the user the agenda is insufficient."""
        safe_summary = (event.summary or "Meeting").replace('"', '\\"')
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
            logger.warning("Could not show agenda rejection dialog")
            print(f"\n  AGENDA QUALITY ISSUE: {event.summary}")
            print(f"  {validation_message}")

    def handle_event(self, event: CalendarEvent) -> bool:
        """Full flow for one event: validate agenda -> prompt -> send bot -> mark processed.

        If agenda is missing/poor:
          - First time: sends email to organizer, shows dialog, marks as notified (NOT processed)
          - Re-check: if agenda updated, allows through; if not, skips silently
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
                already_notified = event.event_id in self.state.notified_events

                if not already_notified:
                    # First time seeing this event with bad agenda — notify organizer
                    message = AgendaValidator.build_validation_message(validation)
                    logger.warning(
                        "Agenda rejected for %s (quality=%s, required=%s)",
                        event.summary, validation["quality_level"], Config.AGENDA_MIN_QUALITY,
                    )
                    self._send_agenda_required_email(event, validation)
                    self._show_agenda_rejection_dialog(event, message)
                    self.state.notified_events[event.event_id] = {
                        "notified_at": datetime.now(timezone.utc),
                        "quality": validation["quality_level"],
                    }
                    print(f"  Blocked: {event.summary} — agenda quality too low ({validation['quality_level']})")
                    print(f"  Email sent to organizer. Waiting for agenda update...")
                else:
                    # Already notified — silently skip (will re-check next poll)
                    logger.debug(
                        "Still waiting for agenda update: %s (quality=%s)",
                        event.summary, validation["quality_level"],
                    )
                return False

            # Agenda is now valid — if it was previously notified, log the update
            if event.event_id in self.state.notified_events:
                del self.state.notified_events[event.event_id]
                print(f"  Agenda updated for: {event.summary} — now meets quality threshold!")
                logger.info("Agenda updated for %s, proceeding with bot invite", event.summary)

        # --- Normal flow: prompt user -> send bot ---
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

    def _run_tracker_for_event(self, event: CalendarEvent) -> None:
        """Run a MeetingFocusTracker for a single event (called in a thread)."""
        from tracker import MeetingFocusTracker

        description = event.description or event.summary

        print(f"\n  [{event.meet_id}] Starting tracker for: {event.summary}")
        try:
            # Set Config values for tracker initialization
            Config.MEETING_ID = event.meet_id

            # Build email recipient list from calendar attendees + organizer.
            # Gmail API will send to these automatically — no .env config needed.
            email_recipients: list[str] = []
            seen: set[str] = set()
            for addr in list(event.attendees) + [event.organizer_email]:
                if addr and addr not in seen:
                    email_recipients.append(addr)
                    seen.add(addr)

            tracker = MeetingFocusTracker(
                google_creds=self.google_creds,
                attendees=email_recipients,
                meeting_title=event.summary,
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
