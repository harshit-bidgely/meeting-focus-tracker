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
from services.llm_client import LLMClient
from services.meeting_memory import MeetingMemory
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
    had_transcript: bool = False          # True once we've seen real transcript
    empty_cycles_since_data: int = 0      # consecutive empty cycles after data


class MeetingFocusTracker:
    """Main orchestrator — extracts agenda, polls transcript, analyses focus, sends alerts."""

    def __init__(self) -> None:
        self.vexa = VexaClient(api_base=Config.VEXA_API_BASE, api_key=Config.VEXA_API_KEY)
        self.llm = LLMClient(api_key=Config.LLM_API_KEY, model=Config.LLM_MODEL, api_base=Config.LLM_API_BASE)
        self.memory = MeetingMemory(storage_path=Config.MEMORY_STORAGE_PATH)
        self.state = MeetingState()
        self.agenda_formatted: str = ""
        self.agenda_items: list[str] = []
        self.past_context: str = ""
        self.platform: str = Config.MEETING_PLATFORM
        self.meeting_id: str = Config.MEETING_ID

    # ------------------------------------------------------------------
    # Step 1: agenda extraction (runs once)
    # ------------------------------------------------------------------

    def extract_agenda(self, description: str) -> str:
        """Call Prompt 1 to extract a structured agenda. Returns formatted string."""
        logger.info("Extracting agenda from calendar description (%d chars)", len(description))
        result = self.llm.call(
            system_prompt=AGENDA_EXTRACTOR_SYSTEM,
            user_message=description,
            max_tokens=512,
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
        safe_reason = reason.replace('"', '\\"')
        safe_suggestion = suggestion.replace('"', '\\"')
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
                            if self.state.empty_cycles_since_data >= 3:
                                print(f"\n[Cycle {cycle}] Meeting appears to have ended (no new transcript for {self.state.empty_cycles_since_data} cycles)")
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
        """Persist current meeting summary to local memory."""
        from datetime import datetime, timezone
        try:
            summary = self.state.rolling_summary
            decisions = []
            open_items = []
            for line in summary.replace("\\n", "\n").split("\n"):
                lower = line.lower()
                if "done:" in lower or "decided" in lower:
                    decisions.append(line.strip())
                elif "not_started" in lower or "pending" in lower or "tbd" in lower:
                    open_items.append(line.strip())

            self.memory.save_meeting(
                meeting_id=self.meeting_id,
                date=datetime.now(timezone.utc).isoformat(),
                agenda_raw=self.agenda_formatted,
                agenda_items=self.agenda_items,
                final_summary=summary,
                decisions=decisions,
                open_items=open_items,
                deviation_count=int(self.state.deviation_counter),
            )
            logger.info("Meeting saved to memory")
        except Exception:
            logger.exception("Failed to save meeting to memory")

    def _sleep_remaining(self, cycle_start: float) -> None:
        """Sleep for the remainder of the poll interval."""
        elapsed = time.time() - cycle_start
        remaining = max(0, Config.POLL_INTERVAL - elapsed)
        if remaining > 0:
            time.sleep(remaining)
