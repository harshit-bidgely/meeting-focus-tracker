from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field

import re as _re

from config import Config
from prompts.agenda_extractor import AGENDA_EXTRACTOR_SYSTEM
from prompts.focus_tracker import FOCUS_TRACKER_SYSTEM, build_user_message
from prompts.repetition_detector import build_repetition_suffix
from prompts.summary_generator import SUMMARY_GENERATOR_SYSTEM, build_summary_message
from services.llm_client import LLMClient
from services.meeting_memory import MeetingMemory
from services.similarity import generate_thread_insight
from services.thread_store import save_meeting_to_thread, find_matching_thread, get_thread_meetings
from services.transcript_cleaner import clean_segments, count_meaningful_words
from services.vexa_client import VexaClient

logger = logging.getLogger(__name__)

# Deviation level icons for console output
LEVEL_ICONS = {
    "on_track": "\u2705",
    "tangential": "\U0001f7e1",
    "off_topic": "\U0001f534",
    "insufficient_data": "\u2796",
}


@dataclass
class MeetingState:
    """All state that persists across cycles."""

    rolling_summary: str = ""
    current_agenda_item: int | None = None
    last_segment_timestamp: str | None = None
    deviation_counter: float = 0.0
    last_alert_time: float = 0.0
    cycle_count: int = 0
    full_transcript: str = ""
    had_transcript: bool = False          # True once we've seen real transcript
    empty_cycles_since_data: int = 0      # consecutive empty cycles after data


class MeetingFocusTracker:
    """Main orchestrator — extracts agenda, polls transcript, analyses focus, sends alerts."""

    def __init__(
        self,
        meeting_id: str | None = None,
        google_creds=None,
        meeting_title: str = "",
        attendees: list[str] | None = None,
    ) -> None:
        self.vexa = VexaClient(api_base=Config.VEXA_API_BASE, api_key=Config.VEXA_API_KEY)
        self.llm = LLMClient(api_key=Config.LLM_API_KEY, model=Config.LLM_MODEL, api_base=Config.LLM_API_BASE)
        self.memory = MeetingMemory(storage_path=Config.MEMORY_STORAGE_PATH)
        self.state = MeetingState()
        self.agenda_formatted: str = ""
        self.agenda_items: list[str] = []
        self.past_context: str = ""
        self.platform: str = Config.MEETING_PLATFORM
        self.meeting_id: str = meeting_id or Config.MEETING_ID or ""
        self.google_creds = google_creds
        self.meeting_title: str = meeting_title
        self.attendees: list[str] = attendees or []

    # ------------------------------------------------------------------
    # Step 1: agenda extraction (runs once)
    # ------------------------------------------------------------------

    def extract_agenda(self, description: str) -> str:
        """Call Prompt 1 to extract a structured agenda. Returns formatted string."""
        logger.info("Extracting agenda from calendar description (%d chars)", len(description))
        result = self.llm.call(
            system_prompt=AGENDA_EXTRACTOR_SYSTEM,
            user_message=description,
            max_tokens=1024,
        )
        status = result.get("status", "")
        if status == "no_agenda_found":
            logger.warning("No agenda found in calendar description")
            return ""
        formatted = result.get("formatted", "")
        logger.info("Agenda extracted:\n%s", formatted)

        # Parse individual topic strings for memory matching
        self.agenda_items = [
            _re.sub(r"^\d+\.\s*", "", line).strip().split("(")[0].strip()
            for line in formatted.split("\n")
            if line.strip()
        ]
        return formatted

    def load_past_context(self) -> None:
        """Query meeting memory for related past meetings and build context string."""
        if not self.agenda_items:
            return
        related = self.memory.find_related_meetings(
            self.agenda_items,
            max_results=3,
            threshold=Config.MEMORY_SIMILARITY_THRESHOLD,
        )
        if related:
            raw_context = self.memory.build_context_summary(related)
            self.past_context = build_repetition_suffix(raw_context)
            logger.info("Found %d related past meetings", len(related))
        else:
            logger.info("No related past meetings found")

    # ------------------------------------------------------------------
    # Step 2: fetch new transcript chunk
    # ------------------------------------------------------------------

    def fetch_new_transcript(self) -> str:
        """Fetch transcript from Vexa, clean, and return new text since last poll."""
        data = self.vexa.get_transcript(self.platform, self.meeting_id)
        segments = data.get("segments", [])
        if not segments:
            logger.debug("No segments returned from Vexa")
            return ""

        cleaned_text, latest_ts = clean_segments(
            segments, after_timestamp=self.state.last_segment_timestamp
        )
        if latest_ts:
            self.state.last_segment_timestamp = latest_ts
        return cleaned_text

    def fetch_full_transcript(self) -> str:
        """Fetch the COMPLETE transcript from Vexa (no timestamp filter). Used on exit."""
        data = self.vexa.get_transcript(self.platform, self.meeting_id)
        segments = data.get("segments", [])
        if not segments:
            return ""
        cleaned_text, _ = clean_segments(segments, after_timestamp=None)
        return cleaned_text

    # ------------------------------------------------------------------
    # Step 3: LLM analysis
    # ------------------------------------------------------------------

    def analyze(self, new_transcript: str) -> dict:
        """Run Prompt 2 — focus tracker — and return parsed JSON result."""
        user_msg = build_user_message(
            agenda=self.agenda_formatted,
            rolling_summary=self.state.rolling_summary,
            current_item=self.state.current_agenda_item,
            new_transcript=new_transcript,
            past_context=self.past_context,
        )
        return self.llm.call(
            system_prompt=FOCUS_TRACKER_SYSTEM,
            user_message=user_msg,
            max_tokens=2048,
        )

    # ------------------------------------------------------------------
    # Step 4: state update
    # ------------------------------------------------------------------

    def update_state(self, result: dict) -> None:
        """Update rolling summary, current item, and deviation counter."""
        self.state.rolling_summary = result.get("updated_summary", self.state.rolling_summary)
        self.state.current_agenda_item = result.get(
            "current_agenda_item_number", self.state.current_agenda_item
        )

        level = result.get("deviation_level", "insufficient_data")
        if level == "off_topic":
            self.state.deviation_counter += 1
        elif level == "tangential":
            self.state.deviation_counter += 0.5
        else:
            # on_track or insufficient_data → full reset
            self.state.deviation_counter = 0

        logger.debug(
            "State updated — item=%s, deviation_counter=%.1f",
            self.state.current_agenda_item,
            self.state.deviation_counter,
        )

    # ------------------------------------------------------------------
    # Step 5: alert logic
    # ------------------------------------------------------------------

    def maybe_send_alert(self, result: dict) -> bool:
        """Send an alert into the meeting chat if deviation threshold is met.

        Returns True if an alert was sent.
        """
        if self.state.deviation_counter < Config.DEVIATION_THRESHOLD:
            return False

        now = time.time()
        if (now - self.state.last_alert_time) < Config.ALERT_COOLDOWN:
            logger.info(
                "Alert suppressed — cooldown active (%.0fs remaining)",
                Config.ALERT_COOLDOWN - (now - self.state.last_alert_time),
            )
            return False

        level = result.get("deviation_level", "off_topic")
        reason = result.get("reason", "Discussion has drifted from the agenda.")
        suggestion = result.get("suggestion", "Consider returning to the agenda.")

        if level == "off_topic":
            message = f"\U0001f534 Off Topic: {reason}\n\U0001f4a1 Suggestion: {suggestion}"
        else:
            message = f"\U0001f7e1 Drifting: {reason}\n\U0001f4a1 Suggestion: {suggestion}"

        # macOS desktop notification — pops up on screen over Google Meet
        notif_title = "Off Topic!" if level == "off_topic" else "Drifting!"
        # Escape double quotes for AppleScript
        safe_reason = (reason or "").replace('"', '\\"')
        safe_suggestion = (suggestion or "Consider returning to the agenda.").replace('"', '\\"')
        applescript = (
            f'display notification "{safe_reason}\\n{safe_suggestion}" '
            f'with title "Meeting Focus Tracker" '
            f'subtitle "{notif_title}" '
            f'sound name "Blow"'
        )
        try:
            subprocess.Popen(["osascript", "-e", applescript])
            logger.info("Desktop notification sent")
        except Exception:
            logger.debug("Desktop notification failed")

        # Also try Vexa chat API (may not be available)
        try:
            self.vexa.send_chat(self.platform, self.meeting_id, message)
        except Exception:
            pass

        # Console alert
        print(f"\n{'='*60}")
        print(f"  ALERT: {message}")
        print(f"{'='*60}\n")
        self.state.last_alert_time = now
        return True

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, calendar_description: str) -> None:
        """Run the focus tracker loop."""
        # 1. Extract agenda
        self.agenda_formatted = self.extract_agenda(calendar_description)
        if not self.agenda_formatted:
            print("No agenda could be extracted from the calendar description. Exiting.")
            return

        # 1b. Load past meeting context
        self.load_past_context()

        # 2. Startup banner
        print("\n" + "=" * 60)
        print("  MEETING FOCUS TRACKER")
        print("=" * 60)
        print(f"  Platform : {self.platform}")
        print(f"  Meeting  : {self.meeting_id}")
        print(f"  Poll     : every {Config.POLL_INTERVAL}s")
        print(f"  Threshold: {Config.DEVIATION_THRESHOLD} consecutive deviations")
        print(f"  Cooldown : {Config.ALERT_COOLDOWN}s between alerts")
        print("-" * 60)
        print("  AGENDA:")
        for line in self.agenda_formatted.split("\n"):
            print(f"    {line}")
        if self.past_context:
            print("-" * 60)
            print("  MEMORY: Found related previous meetings")
        print("=" * 60 + "\n")

        # 2b. Request bot to join
        try:
            self.vexa.start_bot(self.platform, self.meeting_id)
            print("  Bot join requested — admit 'FocusBot' in Google Meet when it appears\n")
        except Exception as e:
            logger.warning("Bot join request failed (may already be in meeting): %s", e)

        # 3. Infinite loop
        try:
            while True:
                cycle_start = time.time()
                self.state.cycle_count += 1
                cycle = self.state.cycle_count

                try:
                    # a. Fetch new transcript
                    new_transcript = self.fetch_new_transcript()

                    # b. Skip if not enough data
                    if count_meaningful_words(new_transcript) < 5:
                        print(f"[Cycle {cycle}] -- Insufficient new transcript, skipping analysis")
                        # Track empty cycles after we've had real data
                        if self.state.had_transcript:
                            self.state.empty_cycles_since_data += 1
                            if self.state.empty_cycles_since_data >= 1:
                                time.sleep(2)
                                # One final check to be sure
                                final_transcript = self.fetch_new_transcript()
                                if count_meaningful_words(final_transcript) >= 5:
                                    self.state.empty_cycles_since_data = 0
                                    self.state.full_transcript += "\n" + final_transcript
                                    continue
                                print(f"\n[Cycle {cycle}] Meeting ended — no new transcript.")
                                print("Saving meeting to memory...")
                                self._save_to_memory()
                                print("Meeting saved. Exiting.")
                                return
                        self._sleep_remaining(cycle_start)
                        continue

                    # Reset empty cycle counter when we get data
                    self.state.had_transcript = True
                    self.state.empty_cycles_since_data = 0

                    # c. Analyse
                    result = self.analyze(new_transcript)

                    # d. Pretty-print
                    level = result.get("deviation_level", "?")
                    icon = LEVEL_ICONS.get(level, "?")
                    topic = result.get("current_topic", "")
                    reason = result.get("reason", "")
                    suggestion = result.get("suggestion")
                    confidence = result.get("confidence", 0)
                    summary = result.get("updated_summary", "")

                    print(f"\n{'─'*60}")
                    print(f"[Cycle {cycle}] {icon} {level.upper():18s} | {topic}")
                    print(f"  Reason     : {reason}")
                    if suggestion:
                        print(f"  Suggestion : {suggestion}")
                    print(f"  Confidence : {confidence}")
                    print(f"  Deviation# : {self.state.deviation_counter + (1 if level == 'off_topic' else 0.5 if level == 'tangential' else 0)}")
                    print(f"  ── Transcript ──")
                    for line in new_transcript.split("\n")[:5]:
                        print(f"    {line[:100]}")
                    if len(new_transcript.split("\n")) > 5:
                        print(f"    ... (+{len(new_transcript.split(chr(10))) - 5} more lines)")
                    rep_detected = result.get("repetition_detected", False)
                    rep_note = result.get("repetition_note")
                    if rep_detected and rep_note:
                        print(f"  REPEAT     : {rep_note}")
                    elif rep_note:
                        print(f"  PROGRESS   : {rep_note}")
                    print(f"  ── Rolling Summary ──")
                    for line in summary.replace("\\n", "\n").split("\n"):
                        if line.strip():
                            print(f"    {line.strip()}")
                    print(f"{'─'*60}")

                    # e. State update
                    self.update_state(result)

                    # f. Alert check
                    alert_sent = self.maybe_send_alert(result)
                    if alert_sent:
                        print(f"[Cycle {cycle}] >>> ALERT sent to meeting chat <<<")

                except Exception:
                    logger.exception("Error in cycle %d", cycle)
                    print(f"[Cycle {cycle}] ERROR — see logs. Continuing...")

                self._sleep_remaining(cycle_start)

        except KeyboardInterrupt:
            print("\nSaving meeting to memory...")
            self._save_to_memory()
            print("Stopping focus tracker. Goodbye!")

    def _save_to_memory(self) -> None:
        """Persist meeting: transcript + summary + thread grouping + memory + G Suite exports."""
        from datetime import datetime, timezone

        now = datetime.now()
        rolling = self.state.rolling_summary

        # 1. Fetch COMPLETE transcript from Vexa (not cycle deltas)
        print("  Fetching complete transcript from Vexa...")
        time.sleep(3)  # let Vexa flush final segments
        raw_transcript = self.fetch_full_transcript()
        if not raw_transcript.strip():
            raw_transcript = self.state.full_transcript or ""

        # 2. Build structured transcript with metadata header
        transcript_lines = [
            f"MEETING TRANSCRIPT",
            f"{'='*50}",
            f"Meeting ID : {self.meeting_id}",
            f"Date       : {now.strftime('%Y-%m-%d %H:%M')}",
            f"Platform   : {self.platform}",
            f"Agenda     : {self.agenda_formatted.replace(chr(10), ' | ')}",
            f"{'='*50}",
            f"",
        ]
        if raw_transcript.strip():
            transcript_lines.append(raw_transcript)
        else:
            transcript_lines.append("(no transcript captured)")
        full_transcript = "\n".join(transcript_lines)

        # 3. Generate LLM-powered structured summary
        print("  Generating meeting summary...")
        try:
            summary_data = self.llm.call(
                system_prompt=SUMMARY_GENERATOR_SYSTEM,
                user_message=build_summary_message(
                    agenda=self.agenda_formatted,
                    rolling_summary=rolling,
                    full_transcript=raw_transcript,
                ),
                max_tokens=2048,
            )
            # Inject metadata the LLM doesn't know
            summary_data["meeting_id"] = self.meeting_id
            summary_data["date"] = now.isoformat()
            summary_data["platform"] = self.platform
            summary_data["agenda_raw"] = self.agenda_formatted
            summary_data["deviation_count"] = int(self.state.deviation_counter)
        except Exception:
            logger.exception("LLM summary generation failed, using fallback")
            summary_data = {
                "meeting_id": self.meeting_id,
                "date": now.isoformat(),
                "agenda_raw": self.agenda_formatted,
                "agenda_items": self.agenda_items,
                "rolling_summary": rolling,
                "title": f"Meeting {self.meeting_id} — {now.strftime('%Y-%m-%d %H:%M')}",
                "deviation_count": int(self.state.deviation_counter),
            }

        # Extract decisions/open_items for memory storage
        decisions = []
        open_items = []
        for item in summary_data.get("agenda_items", []):
            if isinstance(item, dict):
                decisions.extend(item.get("decisions", []))
                open_items.extend(item.get("action_items", []))
        for a in summary_data.get("overall_action_items", []):
            if isinstance(a, dict):
                open_items.append(a.get("action", ""))

        try:
            # 4. Save to thread structure (transcript + summary grouped by agenda)
            meeting_dir = save_meeting_to_thread(
                meeting_id=self.meeting_id,
                agenda=self.agenda_formatted,
                agenda_items=self.agenda_items,
                summary=summary_data,
                transcript=full_transcript,
                rolling_summary=rolling,
            )
            print(f"  Saved to thread: {meeting_dir}")

            # 5. Also save to flat meeting memory (for fuzzy matching / LLM context injection)
            self.memory.save_meeting(
                meeting_id=self.meeting_id,
                date=datetime.now(timezone.utc).isoformat(),
                agenda_raw=self.agenda_formatted,
                agenda_items=self.agenda_items,
                final_summary=rolling,
                decisions=decisions,
                open_items=open_items,
                deviation_count=int(self.state.deviation_counter),
            )

            # 6. Thread insight
            thread_dir = find_matching_thread(self.agenda_formatted)
            if thread_dir:
                thread_meetings = get_thread_meetings(thread_dir)
                if len(thread_meetings) >= 2:
                    print(f"\n{'─'*60}")
                    print(f"  THREAD HISTORY ({len(thread_meetings)} meetings on this agenda)")
                    print(f"{'─'*60}")
                    for m in thread_meetings:
                        date_str = m.get("date", "")[:16].replace("T", " ")
                        title = m.get("title", "Untitled")[:50]
                        print(f"    {date_str}  {title}")
                    print(f"{'─'*60}")

            all_related = self.memory.find_related_meetings(
                self.agenda_items, max_results=10, threshold=0.4
            )
            if len(all_related) >= 2:
                thread = generate_thread_insight(all_related)
                print(f"\n{'─'*60}")
                print(f"  REPETITION ANALYSIS ({thread['total_meetings']} meetings)")
                print(f"{'─'*60}")
                print(f"  Repetition : {thread['repetition_pct']}%")
                if thread.get("repeated_topics"):
                    print(f"  Recurring  : {', '.join(str(t) for t in thread['repeated_topics'][:5])}")
                print(f"  Decisions  : {thread.get('total_decisions', 0)} total across thread")
                print(f"  Insight    : {thread['insight']}")
                print(f"{'─'*60}")

            logger.info("Meeting saved to memory")

            # 7. Export to Google Workspace
            title = self.meeting_title or f"Meeting {self.meeting_id}"
            deviation_count = int(self.state.deviation_counter)
            summary_text = rolling

            self._export_to_google_drive(title, summary_text, decisions, open_items, deviation_count)
            self._export_to_gmail(title, summary_text, decisions, open_items, deviation_count)

        except Exception:
            logger.exception("Failed to save meeting to memory")

    def _export_to_google_drive(
        self, title: str, summary: str, decisions: list[str],
        open_items: list[str], deviation_count: int,
    ) -> None:
        """Save meeting notes to Google Drive if enabled."""
        if not Config.ENABLE_GOOGLE_DRIVE or not self.google_creds:
            return
        try:
            from services.google_drive import GoogleDriveService
            drive = GoogleDriveService(self.google_creds)
            doc_url = drive.save_meeting_notes(
                meeting_title=title,
                agenda=self.agenda_formatted,
                summary=summary,
                decisions=decisions,
                open_items=open_items,
                deviation_count=deviation_count,
            )
            if doc_url:
                print(f"  Meeting notes saved to Google Drive: {doc_url}")
        except Exception:
            logger.exception("Google Drive export failed")

    def _export_to_gmail(
        self, title: str, summary: str, decisions: list[str],
        open_items: list[str], deviation_count: int,
    ) -> None:
        """Email meeting summary to attendees if enabled."""
        if not Config.ENABLE_GMAIL_SUMMARY or not self.google_creds:
            return
        if not self.attendees:
            logger.info("Gmail export skipped — no attendees to email")
            return
        try:
            from services.gmail_service import GmailService
            gmail = GmailService(self.google_creds)
            sent = gmail.send_meeting_summary(
                to_emails=self.attendees,
                meeting_title=title,
                agenda=self.agenda_formatted,
                summary=summary,
                decisions=decisions,
                open_items=open_items,
                deviation_count=deviation_count,
            )
            if sent:
                print(f"  Meeting summary emailed to {len(self.attendees)} attendees")
        except Exception:
            logger.exception("Gmail export failed")

    def _sleep_remaining(self, cycle_start: float) -> None:
        """Sleep for the remainder of the poll interval."""
        elapsed = time.time() - cycle_start
        remaining = max(0, Config.POLL_INTERVAL - elapsed)
        if remaining > 0:
            time.sleep(remaining)
