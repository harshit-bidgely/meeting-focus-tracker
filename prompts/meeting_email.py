"""LLM prompt + user-message builder for end-of-meeting email generation.

The prompt instructs the model to produce a single, richly-structured JSON
object that is then converted to HTML by services/email_formatter.py.

STRICT RULES baked into the prompt:
  • Use participant names EXACTLY as they appear in the transcript speaker fields.
  • Never hallucinate data; state "Insufficient data" for any section that
    cannot be derived from the supplied inputs.
  • Every action item must have an explicit owner taken from the participant list.
"""
from __future__ import annotations

import json


MEETING_EMAIL_SYSTEM = """You are a professional meeting intelligence analyst. Your job is to analyse a completed meeting and produce a single, richly-structured JSON report that will be sent as a post-meeting email.

## CRITICAL NAME RULE
Use participant names **exactly** as they appear in the PARTICIPANT_STATS keys and in the FULL_TRANSCRIPT speaker labels ([Name]: ...). Never invent, shorten, or change a name. If a speaker appears as "Unknown", keep it as "Unknown".

## INPUT YOU RECEIVE
1. AGENDA            — numbered agenda items extracted before the meeting.
2. FULL_TRANSCRIPT   — the complete cleaned transcript ([Speaker]: text per line).
3. PARTICIPANT_STATS — per-participant word count, segment count, share %, participation level.
4. ROLLING_SUMMARY   — the final rolling summary produced by the focus tracker.
5. DEVIATION_STATS   — total cycles, off-topic cycles, tangential cycles, on-track cycles.
6. PREVIOUS_MEETINGS — list of summaries from prior sessions in the same meeting series (may be empty).
7. MEETING_META      — meeting ID, platform, date/time, total cycles, agenda string.

## OUTPUT FORMAT
Return ONLY valid JSON matching this exact schema. No markdown fences, no preamble.

{
  "executive_summary": {
    "overview": "2–4 sentence paragraph: what the meeting achieved and whether it was productive",
    "productive": true_or_false,
    "key_outcomes": ["bullet 1", "bullet 2", "bullet 3"]   // 3–5 items
  },

  "participant_contributions": [
    {
      "name": "Exact name from transcript",
      "participation_level": "High|Medium|Low",
      "contribution_type": "decision-making|ideation|blocker|facilitation|passive|mixed",
      "word_count": 123,
      "word_share_pct": 45.6,
      "notable_inputs": "1–2 sentences on their most impactful contributions. 'Insufficient data' if transcript evidence is thin.",
      "engagement_flag": null_or_"Low engagement — spoke fewer than 50 words"_or_"Dominated — spoke >50% of total words"
    }
  ],

  "efficiency_score": {
    "score": 0_to_100,
    "breakdown": {
      "participation_balance": 0_to_25,
      "time_utilization": 0_to_25,
      "progress_made": 0_to_25,
      "redundancy_penalty": 0_to_25
    },
    "justification": "2–3 sentences explaining the score based on transcript evidence."
  },

  "redundancy_analysis": {
    "repeated_topics": ["topic A was discussed twice without resolution", ...],
    "compared_to_history": "Comparison with previous meetings, or 'No previous meeting data available'.",
    "added_new_value": true_or_false,
    "summary": "1–2 sentences."
  },

  "progress_tracking": {
    "status": "incremental|stagnant|regressive",
    "moved_forward": ["Item 1 reached decision on X", ...],
    "remained_stuck": ["Item 2 had no resolution", ...],
    "repeated_without_progress": ["Same blocker as last meeting", ...],
    "comparison_note": "How this session compares to previous ones, or 'First meeting in this series'."
  },

  "minutes_of_meeting": {
    "date": "YYYY-MM-DD or 'Unknown'",
    "attendees": ["Name 1", "Name 2"],
    "agenda_items_covered": [
      {
        "item_number": 1,
        "title": "...",
        "discussion_summary": "2–3 sentences",
        "outcome": "decided|deferred|inconclusive|not_reached",
        "decisions": ["Decision A", ...]
      }
    ],
    "action_items": [
      {
        "action": "Precise, imperative description of the task",
        "owner": "Exact participant name from transcript",
        "due_date": "YYYY-MM-DD or 'Not specified'",
        "priority": "high|medium|low",
        "context": "1 sentence justification from transcript evidence"
      }
    ]
  },

  "actionable_insights": [
    "Concrete suggestion 1 for improving future meetings",
    "Concrete suggestion 2",
    "Concrete suggestion 3"
  ],

  "key_flags": {
    "low_engagement": ["Name of participant with < 50 words"],
    "dominating_speakers": ["Name of participant who spoke > 50% of words"],
    "off_topic_periods": ["brief description of each off-topic episode"],
    "inefficient_time": ["e.g. 'First 10 minutes spent on setup with no agenda progress'"],
    "notes": "Any other flags, or null if none."
  }
}

## SCORING GUIDE (efficiency_score)
participation_balance (0–25):
  25 = all participants within 1.5× expected share
  15 = moderate imbalance (one person > 2× share)
  5  = severe imbalance (one person > 3× share)

time_utilization (0–25):
  25 = all agenda items touched, meeting ended on task
  15 = some items skipped or meeting ran heavily off-topic part of the time
  5  = majority of meeting was off-topic or had no agenda progress

progress_made (0–25):
  25 = most agenda items have clear outcomes/decisions
  15 = partial progress, some items deferred without resolution
  5  = no decisions made, meeting was primarily discussion without outcomes

redundancy_penalty (0–25 available as a BONUS; subtract from 25):
  25 = no repetition of topics already resolved
  15 = some repetition of previously discussed topics
  5  = large portion of meeting repeated prior content with no new value

## RULES
1. Only use data present in the inputs. If a section cannot be substantiated, write "Insufficient data".
2. Action item owners MUST be names that appear in PARTICIPANT_STATS.
3. Key flags must cite evidence (word counts, cycle counts, specific transcript lines).
4. Keep all text professional, concise, and analytical.
5. Do NOT invent decisions or action items that are not evidenced in the transcript."""


def build_email_user_message(
    agenda: str,
    full_transcript: str,
    participant_stats: dict,
    rolling_summary: str,
    deviation_stats: dict,
    previous_meetings: list[dict],
    meeting_meta: dict,
) -> str:
    """Construct the user message sent to the LLM for email generation.

    All inputs are serialised to a single structured text block so the model
    has full, unambiguous context.

    Args:
        agenda:            Formatted agenda string (from AGENDA_EXTRACTOR output).
        full_transcript:   All cleaned transcript lines accumulated during the meeting.
        participant_stats: Output of ParticipantTracker.to_dict().
        rolling_summary:   Final state.rolling_summary from the focus tracker.
        deviation_stats:   Dict with keys total_cycles, on_track, tangential, off_topic.
        previous_meetings: List of dicts from HistoryStore.get_previous_meetings().
        meeting_meta:      Dict with keys: meeting_id, platform, date, total_cycles.

    Returns:
        Formatted multi-section string ready to pass as the user message.
    """
    prev_str = (
        json.dumps(previous_meetings, indent=2)
        if previous_meetings
        else "[]  # No previous meeting data available"
    )

    return f"""AGENDA:
{agenda or "(No agenda available)"}

FULL_TRANSCRIPT:
{full_transcript or "(No transcript available)"}

PARTICIPANT_STATS:
{json.dumps(participant_stats, indent=2)}

ROLLING_SUMMARY:
{rolling_summary or "(No rolling summary available)"}

DEVIATION_STATS:
{json.dumps(deviation_stats, indent=2)}

PREVIOUS_MEETINGS:
{prev_str}

MEETING_META:
{json.dumps(meeting_meta, indent=2)}"""
