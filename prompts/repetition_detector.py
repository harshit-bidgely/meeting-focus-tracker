from __future__ import annotations


PAST_CONTEXT_BLOCK = """
## PAST MEETING CONTEXT
The following is a summary of previous meetings that covered similar agenda items.
Use this to detect:
- REPETITION: Topics being re-discussed without new information or progress
- PROGRESS: Decisions made previously that are being built upon
- REGRESSION: Previously resolved items being reopened

When you detect repetition, set "repetition_detected" to true and explain in "repetition_note".
When you detect progress on a previous decision, note it positively in "repetition_note".

{past_context}
"""


def build_repetition_suffix(past_context: str) -> str:
    """Return formatted past context block, or empty string if no context."""
    if not past_context.strip():
        return ""
    return PAST_CONTEXT_BLOCK.format(past_context=past_context)
