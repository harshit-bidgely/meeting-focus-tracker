"""Google Calendar integration.

Fetches the current or next upcoming meeting from Google Calendar,
extracts the agenda (description) and Google Meet link/ID automatically.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from dataclasses import dataclass

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    """Parsed calendar event with meeting-relevant fields."""

    event_id: str
    summary: str
    description: str
    meet_id: str | None
    start_time: datetime
    end_time: datetime
    attendees: list[str]


class GoogleCalendarService:
    """Reads events from Google Calendar to auto-populate meeting details."""

    def __init__(self, credentials: Credentials) -> None:
        self.service = build("calendar", "v3", credentials=credentials)

    def get_current_or_next_event(self, calendar_id: str = "primary") -> CalendarEvent | None:
        """Find the event that is happening right now, or the next upcoming one.

        Returns None if no events are found in the next 24 hours.
        """
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        # Look ahead 24 hours
        time_max = datetime(
            now.year, now.month, now.day, now.hour, now.minute, now.second,
            tzinfo=timezone.utc,
        )
        from datetime import timedelta
        time_max = (now + timedelta(hours=24)).isoformat()

        logger.info("Fetching calendar events from %s", time_min[:19])

        result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=5,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = result.get("items", [])
        if not events:
            logger.info("No upcoming events found in the next 24 hours")
            return None

        # Prefer an event that is currently in progress
        for event in events:
            parsed = self._parse_event(event)
            if parsed and parsed.start_time <= now <= parsed.end_time:
                logger.info("Found in-progress event: %s", parsed.summary)
                return parsed

        # Otherwise return the next upcoming event
        for event in events:
            parsed = self._parse_event(event)
            if parsed:
                logger.info("Found next upcoming event: %s", parsed.summary)
                return parsed

        return None

    def get_event_by_meet_id(self, meet_id: str, calendar_id: str = "primary") -> CalendarEvent | None:
        """Search recent events for one matching a specific Google Meet ID."""
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        time_min = (now - timedelta(hours=2)).isoformat()
        time_max = (now + timedelta(hours=8)).isoformat()

        result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        for event in result.get("items", []):
            parsed = self._parse_event(event)
            if parsed and parsed.meet_id == meet_id:
                return parsed

        return None

    def _parse_event(self, event: dict) -> CalendarEvent | None:
        """Parse a raw Google Calendar API event into a CalendarEvent."""
        start_raw = event.get("start", {}).get("dateTime")
        end_raw = event.get("end", {}).get("dateTime")
        if not start_raw or not end_raw:
            # All-day events don't have dateTime — skip them
            return None

        start_time = datetime.fromisoformat(start_raw)
        end_time = datetime.fromisoformat(end_raw)

        # Extract Google Meet ID from conferenceData or hangoutLink
        meet_id = self._extract_meet_id(event)

        # Extract attendee emails
        attendees = [
            a.get("email", "")
            for a in event.get("attendees", [])
            if not a.get("self", False) and a.get("email")
        ]

        return CalendarEvent(
            event_id=event.get("id", ""),
            summary=event.get("summary", "Untitled Meeting"),
            description=event.get("description", ""),
            meet_id=meet_id,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
        )

    @staticmethod
    def _extract_meet_id(event: dict) -> str | None:
        """Extract the Google Meet meeting code (e.g. 'abc-defg-hij') from an event."""
        # Check conferenceData first (most reliable)
        conf_data = event.get("conferenceData", {})
        for entry_point in conf_data.get("entryPoints", []):
            uri = entry_point.get("uri", "")
            match = re.search(r"meet\.google\.com/([a-z]{3}-[a-z]{4}-[a-z]{3})", uri)
            if match:
                return match.group(1)

        # Fallback: check hangoutLink
        hangout = event.get("hangoutLink", "")
        match = re.search(r"meet\.google\.com/([a-z]{3}-[a-z]{4}-[a-z]{3})", hangout)
        if match:
            return match.group(1)

        # Fallback: check description for a Meet link
        desc = event.get("description", "")
        match = re.search(r"meet\.google\.com/([a-z]{3}-[a-z]{4}-[a-z]{3})", desc)
        if match:
            return match.group(1)

        return None
