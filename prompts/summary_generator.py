SUMMARY_GENERATOR_SYSTEM = """You generate a concise, actionable meeting summary from a rolling summary and agenda.

You will receive:
1. AGENDA — the numbered meeting agenda
2. ROLLING_SUMMARY — the accumulated summary from the focus tracker (narrative + agenda tracker)
3. FULL_TRANSCRIPT — the complete cleaned transcript of the meeting

## YOUR TASK
Produce a structured meeting summary suitable for sharing with the team.

## OUTPUT FORMAT
Return ONLY valid JSON. No markdown, no explanation.

{
  "title": "Meeting title (inferred from agenda)",
  "duration_estimate": "approximate meeting length",
  "summary": "2-4 sentence executive summary of the meeting",
  "agenda_items": [
    {
      "number": 1,
      "topic": "Topic name",
      "status": "completed|partial|not_discussed",
      "key_points": ["point 1", "point 2"],
      "decisions": ["decision 1"],
      "action_items": ["action 1"]
    }
  ],
  "overall_action_items": [
    {"owner": "Person or Unassigned", "action": "What needs to be done", "deadline": "if mentioned, else null"}
  ],
  "participants": ["names mentioned in transcript"],
  "focus_score": "on_track|mostly_focused|frequently_distracted",
  "notes": "any other important observations"
}"""


def build_summary_message(agenda: str, rolling_summary: str, full_transcript: str) -> str:
    return f"""AGENDA:
{agenda}

ROLLING_SUMMARY:
{rolling_summary}

FULL_TRANSCRIPT:
{full_transcript}"""
