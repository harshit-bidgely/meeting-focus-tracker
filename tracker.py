from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from config import Config
from prompts.agenda_extractor import AGENDA_EXTRACTOR_SYSTEM
from prompts.focus_tracker import FOCUS_TRACKER_SYSTEM, build_user_message
from prompts.meeting_email import MEETING_EMAIL_SYSTEM, build_email_user_message
from prompts.meeting_email_professional import MEETING_EMAIL_PROFESSIONAL, build_professional_email_message
from services.email_client import EmailClient
from services.email_formatter import format_email_html, format_email_text
from services.email_formatter_professional import format_professional_html, format_professional_text
from services.history_store import HistoryStore
from services.llm_client import LLMClient
from services.participant_tracker import ParticipantTracker
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
    """All state that persists across cycles.

    Existing fields are unchanged for full backward compatibility.
    New fields use defaults so existing code that constructs MeetingState()
    without arguments continues to work.
    """

    # ── Existing fields (do NOT rename or remove) ─────────────────────────
    rolling_summary: str = ""
    current_agenda_item: int | None = None
    last_segment_timestamp: str | None = None
    deviation_counter: float = 0.0
    last_alert_time: float = 0.0
    cycle_count: int = 0

    # ── New fields added for email/analytics (backward-compatible defaults) ─
    # Accumulated cleaned transcript lines across all cycles (for email generation)
    full_transcript_lines: list[str] = field(default_factory=list)
    # Per-participant contribution tracker
    participant_tracker: ParticipantTracker = field(default_factory=ParticipantTracker)
    # Deviation cycle counters for efficiency scoring
    on_track_cycles: int = 0
    tangential_cycles: int = 0
    off_topic_cycles: int = 0
    # ISO timestamp when the meeting started (set on first transcript fetch)
    meeting_start_time: str | None = None
    # Unix timestamp of last meaningful transcript received (for meeting end detection)
    last_transcript_time: float = 0.0


class MeetingFocusTracker:
    """Main orchestrator — extracts agenda, polls transcript, analyses focus, sends alerts."""

    def __init__(self) -> None:
        self.vexa = VexaClient(api_base=Config.VEXA_API_BASE, api_key=Config.VEXA_API_KEY)
        self.llm = LLMClient(api_key=Config.LLM_API_KEY, model=Config.LLM_MODEL, api_base=Config.LLM_API_BASE)
        self.state = MeetingState()
        self.agenda_formatted: str = ""
        self.platform: str = Config.MEETING_PLATFORM
        self.meeting_id: str = Config.MEETING_ID

        # History store (persists meeting reports across sessions)
        history_kwargs = {}
        if Config.HISTORY_DIR:
            history_kwargs["history_dir"] = Config.HISTORY_DIR
        self.history_store = HistoryStore(**history_kwargs)

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
        return formatted

    # ------------------------------------------------------------------
    # Step 2: fetch new transcript chunk
    # ------------------------------------------------------------------

    def fetch_new_transcript(self) -> str:
        """Fetch transcript from Vexa, clean, and return new text since last poll.

        Also records raw segments into the participant tracker and accumulates
        cleaned lines for end-of-meeting email generation.
        The return type and existing behaviour are unchanged.
        """
        data = self.vexa.get_transcript(self.platform, self.meeting_id)
        segments = data.get("segments", [])
        if not segments:
            logger.debug("No segments returned from Vexa")
            return ""

        # ── NEW: record raw segments into participant tracker ────────────
        self._record_participant_data(segments)

        cleaned_text, latest_ts = clean_segments(
            segments, after_timestamp=self.state.last_segment_timestamp
        )
        if latest_ts:
            self.state.last_segment_timestamp = latest_ts
            if self.state.meeting_start_time is None:
                self.state.meeting_start_time = latest_ts

        # ── NEW: accumulate cleaned lines for full-transcript email ──────
        if cleaned_text:
            self.state.full_transcript_lines.extend(cleaned_text.split("\n"))

        return cleaned_text

    def _record_participant_data(self, segments: list[dict]) -> None:
        """Record raw Vexa segments into the participant tracker.

        Only processes segments newer than last_segment_timestamp (same filter
        logic as clean_segments) so we don't double-count across cycles.
        """
        after_ts = self.state.last_segment_timestamp
        for seg in segments:
            ts = seg.get("absolute_start_time", "")
            text = seg.get("text", "").strip()
            speaker = seg.get("speaker") or "Unknown"
            if not text:
                continue
            # Apply the same timestamp filter used by clean_segments
            if after_ts and ts and ts <= after_ts:
                continue
            self.state.participant_tracker.record_segment(speaker, text, ts)

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
        )
        return self.llm.call(
            system_prompt=FOCUS_TRACKER_SYSTEM,
            user_message=user_msg,
            max_tokens=1024,
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
            self.state.off_topic_cycles += 1
        elif level == "tangential":
            self.state.deviation_counter += 0.5
            self.state.tangential_cycles += 1
        else:
            # on_track or insufficient_data → full reset
            self.state.deviation_counter = 0
            if level == "on_track":
                self.state.on_track_cycles += 1

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
        safe_reason = reason.replace('"', '\\"') if reason else ""
        safe_suggestion = suggestion.replace('"', '\\"') if suggestion else ""
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
    # Post-meeting email generation
    # ------------------------------------------------------------------

    def generate_meeting_report(self) -> dict:
        """Call the LLM to generate a structured post-meeting email JSON.

        Gathers all accumulated state (participant stats, full transcript,
        deviation stats, history) and sends it to the email-generation prompt.

        Returns the parsed JSON dict from the LLM.
        """
        participant_stats = self.state.participant_tracker.to_dict()
        full_transcript = "\n".join(self.state.full_transcript_lines)
        deviation_stats = {
            "total_cycles": self.state.cycle_count,
            "on_track_cycles": self.state.on_track_cycles,
            "tangential_cycles": self.state.tangential_cycles,
            "off_topic_cycles": self.state.off_topic_cycles,
        }
        previous_meetings = self.history_store.get_previous_meetings(
            self.meeting_id or "unknown"
        )
        meeting_date = (
            self.state.meeting_start_time[:10]
            if self.state.meeting_start_time
            else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        meeting_meta = {
            "meeting_id": self.meeting_id or "unknown",
            "platform": self.platform,
            "date": meeting_date,
            "total_cycles": self.state.cycle_count,
        }

        user_msg = build_professional_email_message(
            agenda=self.agenda_formatted,
            full_transcript=full_transcript,
            participant_stats=participant_stats,
            rolling_summary=self.state.rolling_summary,
            deviation_stats=deviation_stats,
            previous_meetings=previous_meetings,
            meeting_meta=meeting_meta,
            meeting_start_time=self.state.meeting_start_time,
        )

        logger.info("Generating professional post-meeting intelligence report via LLM…")
        try:
            report = self.llm.call(
                system_prompt=MEETING_EMAIL_PROFESSIONAL,
                user_message=user_msg,
                max_tokens=8000,  # Much larger for comprehensive professional report
            )
        except Exception:
            logger.exception("LLM call for professional email generation failed")
            report = {}

        return report

    def send_meeting_email(self, report: dict) -> bool:
        """Format *report* as HTML + text and send via SMTP.

        Returns True if the email was dispatched successfully or if email
        is intentionally disabled (SMTP_HOST not configured).
        Saving the report to the history store is always attempted regardless
        of whether the email send succeeds.
        """
        meeting_date = (
            self.state.meeting_start_time[:10]
            if self.state.meeting_start_time
            else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        meeting_meta = {
            "meeting_id": self.meeting_id or "unknown",
            "platform": self.platform,
            "date": meeting_date,
            "total_cycles": self.state.cycle_count,
        }

        # ── Always save to history store ────────────────────────────────
        history_payload = dict(report)
        history_payload["meeting_meta"] = meeting_meta
        history_payload["participant_stats"] = self.state.participant_tracker.to_dict()
        history_payload["deviation_stats"] = {
            "total_cycles": self.state.cycle_count,
            "on_track_cycles": self.state.on_track_cycles,
            "tangential_cycles": self.state.tangential_cycles,
            "off_topic_cycles": self.state.off_topic_cycles,
        }
        try:
            self.history_store.save_meeting(self.meeting_id or "unknown", history_payload)
        except Exception:
            logger.exception("Failed to save meeting to history store")

        # ── Skip email send if SMTP is not configured ───────────────────
        if not Config.email_enabled():
            logger.info(
                "Email not configured (SMTP_HOST / EMAIL_SENDER / EMAIL_RECIPIENTS missing). "
                "Report saved to history store only."
            )
            return True

        html_body = format_professional_html(report, meeting_meta)
        text_body = format_professional_text(report, meeting_meta)

        subject = (
            f"{Config.EMAIL_SUBJECT_PREFIX}: {self.meeting_id or 'Meeting'} — {meeting_date}"
        )

        client = EmailClient(
            smtp_host=Config.SMTP_HOST,
            smtp_port=Config.SMTP_PORT,
            smtp_user=Config.SMTP_USER,
            smtp_password=Config.SMTP_PASSWORD,
            sender_email=Config.EMAIL_SENDER,
            use_tls=Config.SMTP_USE_TLS,
            use_ssl=Config.SMTP_USE_SSL,
        )
        return client.send(
            to_emails=Config.EMAIL_RECIPIENTS,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def _run_post_meeting_pipeline(self) -> None:
        """Generate and send the post-meeting email report.

        Called automatically when the main loop exits (KeyboardInterrupt).
        All errors are caught so they never mask the graceful-exit message.
        """
        if self.state.cycle_count == 0:
            logger.info("No cycles completed — skipping post-meeting report")
            return

        print("\n" + "=" * 60)
        print("  Generating post-meeting intelligence report…")
        print("=" * 60)

        report = self.generate_meeting_report()
        if not report:
            print("  Report generation failed. Check logs.")
            return

        sent = self.send_meeting_email(report)

        if Config.email_enabled():
            status = "sent" if sent else "failed (check logs)"
            print(f"  Email report: {status}")
            if sent:
                print(f"  Recipients : {', '.join(Config.EMAIL_RECIPIENTS)}")
        else:
            print("  Email not configured — report saved to history store only.")

        print("=" * 60 + "\n")

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
        print("=" * 60 + "\n")

        # 3. Infinite loop
        try:
            while True:
                cycle_start = time.time()
                self.state.cycle_count += 1
                cycle = self.state.cycle_count

                try:
                    # a. Fetch new transcript
                    new_transcript = self.fetch_new_transcript()

                    # b. Check if meeting has ended (no new data for 30+ seconds)
                    if count_meaningful_words(new_transcript) < 5:
                        # No meaningful data this cycle
                        if self.state.last_transcript_time > 0:
                            seconds_since_last = time.time() - self.state.last_transcript_time
                            if seconds_since_last > 30:
                                print(f"\n{'='*60}")
                                print(f"[Cycle {cycle}] MEETING ENDED — No activity for {int(seconds_since_last)}s")
                                print(f"{'='*60}")
                                print("Generating final report and sending email...")
                                self._run_post_meeting_pipeline()
                                return
                        print(f"[Cycle {cycle}] -- Insufficient new transcript, skipping analysis")
                        self._sleep_remaining(cycle_start)
                        continue
                    else:
                        # Update last transcript time when we receive new meaningful data
                        self.state.last_transcript_time = time.time()

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
                    print(f"  ── Rolling Summary ──")
                    for line in summary.split("\\n"):
                        print(f"    {line}")
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
            print("\nStopping focus tracker. Goodbye!")
            self._run_post_meeting_pipeline()

    def _sleep_remaining(self, cycle_start: float) -> None:
        """Sleep for the remainder of the poll interval."""
        elapsed = time.time() - cycle_start
        remaining = max(0, Config.POLL_INTERVAL - elapsed)
        if remaining > 0:
            time.sleep(remaining)
