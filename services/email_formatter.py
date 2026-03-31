"""Convert the structured LLM email JSON into HTML and plain-text bodies.

The formatter is intentionally decoupled from both the LLM call and the SMTP
send so each layer can be tested independently.

Backward-compatibility guarantee: this module only *adds* content and never
modifies any existing field in the email_data dict it receives.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(value: object) -> str:
    """HTML-escape a value (converts to str first)."""
    return html.escape(str(value) if value is not None else "")


def _level_badge(level: str) -> str:
    colors = {"High": "#22c55e", "Medium": "#f59e0b", "Low": "#ef4444"}
    bg = colors.get(level, "#6b7280")
    return (
        f'<span style="background:{bg};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:12px;font-weight:600;">{_esc(level)}</span>'
    )


def _score_bar(score: int, max_score: int = 100) -> str:
    pct = max(0, min(100, int(score / max_score * 100)))
    color = "#22c55e" if pct >= 70 else "#f59e0b" if pct >= 40 else "#ef4444"
    return (
        f'<div style="background:#e5e7eb;border-radius:4px;height:12px;width:200px;display:inline-block;">'
        f'<div style="background:{color};width:{pct}%;height:100%;border-radius:4px;"></div>'
        f'</div> <strong>{score}/{max_score}</strong>'
    )


def _section_header(title: str) -> str:
    return (
        f'<h2 style="margin:28px 0 8px;padding-bottom:6px;border-bottom:2px solid #e5e7eb;'
        f'color:#1e293b;font-size:18px;">{_esc(title)}</h2>'
    )


def _ul(items: list, style: str = "") -> str:
    if not items:
        return "<p><em>None</em></p>"
    lis = "".join(f"<li style='margin:4px 0;'>{_esc(it)}</li>" for it in items)
    return f'<ul style="margin:8px 0 8px 20px;{style}">{lis}</ul>'


def _table_row(label: str, value: object, label_width: str = "200px") -> str:
    return (
        f'<tr>'
        f'<td style="padding:6px 12px;font-weight:600;width:{label_width};'
        f'background:#f8fafc;border:1px solid #e2e8f0;vertical-align:top;">{_esc(label)}</td>'
        f'<td style="padding:6px 12px;border:1px solid #e2e8f0;">{_esc(str(value)) if not str(value).startswith("<") else value}</td>'
        f'</tr>'
    )


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_executive_summary(data: dict) -> str:
    es = data.get("executive_summary", {})
    productive = es.get("productive")
    prod_badge = (
        '<span style="color:#22c55e;font-weight:700;">✅ Productive</span>'
        if productive
        else '<span style="color:#ef4444;font-weight:700;">❌ Not Productive</span>'
    )
    outcomes = es.get("key_outcomes") or []
    return (
        _section_header("1. Executive Summary")
        + f'<p style="margin:8px 0;">{_esc(es.get("overview", "Insufficient data"))}</p>'
        + f'<p><strong>Overall Assessment:</strong> {prod_badge}</p>'
        + "<strong>Key Outcomes:</strong>"
        + _ul(outcomes)
    )


def _render_participant_contributions(data: dict) -> str:
    contribs = data.get("participant_contributions") or []
    if not contribs:
        return _section_header("2. Participant Contribution Analysis") + "<p><em>Insufficient data</em></p>"

    rows = ""
    for p in contribs:
        name = _esc(p.get("name", "Unknown"))
        level_html = _level_badge(p.get("participation_level", "Low"))
        ctype = _esc(p.get("contribution_type", "—"))
        wc = _esc(p.get("word_count", 0))
        share = _esc(p.get("word_share_pct", 0))
        notable = _esc(p.get("notable_inputs") or "—")
        flag = p.get("engagement_flag")
        flag_html = (
            f'<br><span style="color:#f59e0b;font-size:12px;">⚠ {_esc(flag)}</span>'
            if flag
            else ""
        )
        rows += (
            f'<tr style="border-bottom:1px solid #e2e8f0;">'
            f'<td style="padding:8px 12px;font-weight:600;">{name}</td>'
            f'<td style="padding:8px 12px;">{level_html}</td>'
            f'<td style="padding:8px 12px;">{ctype}</td>'
            f'<td style="padding:8px 12px;">{wc} ({share}%)</td>'
            f'<td style="padding:8px 12px;">{notable}{flag_html}</td>'
            f'</tr>'
        )

    table = (
        '<table style="width:100%;border-collapse:collapse;margin:12px 0;">'
        '<thead>'
        '<tr style="background:#f1f5f9;">'
        '<th style="padding:8px 12px;text-align:left;border:1px solid #e2e8f0;">Participant</th>'
        '<th style="padding:8px 12px;text-align:left;border:1px solid #e2e8f0;">Level</th>'
        '<th style="padding:8px 12px;text-align:left;border:1px solid #e2e8f0;">Contribution Type</th>'
        '<th style="padding:8px 12px;text-align:left;border:1px solid #e2e8f0;">Words (Share)</th>'
        '<th style="padding:8px 12px;text-align:left;border:1px solid #e2e8f0;">Notable Inputs</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody>'
        '</table>'
    )
    return _section_header("2. Participant Contribution Analysis") + table


def _render_efficiency_score(data: dict) -> str:
    eff = data.get("efficiency_score", {})
    score = eff.get("score", 0)
    breakdown = eff.get("breakdown", {})
    justification = _esc(eff.get("justification", "Insufficient data"))

    breakdown_rows = "".join(
        _table_row(
            label.replace("_", " ").title(),
            f'{breakdown.get(label, 0)} / 25',
        )
        for label in ["participation_balance", "time_utilization", "progress_made", "redundancy_penalty"]
    )

    return (
        _section_header("3. Meeting Efficiency Score")
        + f'<p><strong>Overall Score:</strong> {_score_bar(score)}</p>'
        + '<table style="border-collapse:collapse;margin:8px 0;">'
        + breakdown_rows
        + "</table>"
        + f'<p style="margin-top:8px;"><em>{justification}</em></p>'
    )


def _render_redundancy(data: dict) -> str:
    red = data.get("redundancy_analysis", {})
    repeated = red.get("repeated_topics") or []
    added_val = red.get("added_new_value")
    val_html = (
        '<span style="color:#22c55e;font-weight:600;">✅ Yes</span>'
        if added_val
        else '<span style="color:#ef4444;font-weight:600;">❌ No</span>'
    )

    return (
        _section_header("4. Redundancy & Repetition Analysis")
        + f'<p><strong>Added New Value:</strong> {val_html}</p>'
        + f'<p>{_esc(red.get("summary", "Insufficient data"))}</p>'
        + "<strong>Repeated Topics:</strong>"
        + _ul(repeated)
        + f'<p><strong>Compared to History:</strong> {_esc(red.get("compared_to_history", "No previous meeting data available"))}</p>'
    )


def _render_progress_tracking(data: dict) -> str:
    pt = data.get("progress_tracking", {})
    status = pt.get("status", "unknown")
    status_colors = {"incremental": "#22c55e", "stagnant": "#f59e0b", "regressive": "#ef4444"}
    sc = status_colors.get(status, "#6b7280")
    status_html = (
        f'<span style="background:{sc};color:#fff;padding:3px 10px;'
        f'border-radius:4px;font-weight:600;">{_esc(status.upper())}</span>'
    )

    return (
        _section_header("5. Progress Tracking")
        + f'<p><strong>Meeting Status:</strong> {status_html}</p>'
        + f'<p><em>{_esc(pt.get("comparison_note", "First meeting in this series"))}</em></p>'
        + "<strong>Moved Forward:</strong>" + _ul(pt.get("moved_forward") or [])
        + "<strong>Remained Stuck:</strong>" + _ul(pt.get("remained_stuck") or [])
        + "<strong>Repeated Without Progress:</strong>" + _ul(pt.get("repeated_without_progress") or [])
    )


def _render_mom(data: dict) -> str:
    mom = data.get("minutes_of_meeting", {})
    attendees = mom.get("attendees") or []
    date = _esc(mom.get("date", "Unknown"))
    agenda_items = mom.get("agenda_items_covered") or []
    action_items = mom.get("action_items") or []

    # Agenda items table
    ai_rows = ""
    for item in agenda_items:
        outcome = item.get("outcome", "inconclusive")
        outcome_color = {
            "decided": "#22c55e",
            "deferred": "#f59e0b",
            "inconclusive": "#6b7280",
            "not_reached": "#ef4444",
        }.get(outcome, "#6b7280")
        decisions = "; ".join(item.get("decisions") or []) or "None"
        ai_rows += (
            f'<tr style="border-bottom:1px solid #e2e8f0;">'
            f'<td style="padding:8px 12px;">{_esc(item.get("item_number", "—"))}</td>'
            f'<td style="padding:8px 12px;font-weight:600;">{_esc(item.get("title", "—"))}</td>'
            f'<td style="padding:8px 12px;">{_esc(item.get("discussion_summary", "—"))}</td>'
            f'<td style="padding:8px 12px;"><span style="color:{outcome_color};font-weight:600;">'
            f'{_esc(outcome.replace("_", " ").upper())}</span></td>'
            f'<td style="padding:8px 12px;">{_esc(decisions)}</td>'
            f'</tr>'
        )

    agenda_table = (
        '<table style="width:100%;border-collapse:collapse;margin:12px 0;">'
        '<thead><tr style="background:#f1f5f9;">'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">#</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Topic</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Discussion</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Outcome</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Decisions</th>'
        '</tr></thead>'
        f'<tbody>{ai_rows}</tbody></table>'
    )

    # Action items table
    priority_colors = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}
    action_rows = ""
    for idx, action in enumerate(action_items, 1):
        pri = action.get("priority", "medium")
        pri_color = priority_colors.get(pri, "#6b7280")
        action_rows += (
            f'<tr style="border-bottom:1px solid #e2e8f0;">'
            f'<td style="padding:8px 12px;text-align:center;">{idx}</td>'
            f'<td style="padding:8px 12px;">{_esc(action.get("action", "—"))}</td>'
            f'<td style="padding:8px 12px;font-weight:600;">{_esc(action.get("owner", "—"))}</td>'
            f'<td style="padding:8px 12px;">{_esc(action.get("due_date", "Not specified"))}</td>'
            f'<td style="padding:8px 12px;"><span style="color:{pri_color};font-weight:600;">'
            f'{_esc(pri.upper())}</span></td>'
            f'<td style="padding:8px 12px;font-size:13px;color:#64748b;">{_esc(action.get("context", "—"))}</td>'
            f'</tr>'
        )

    action_table = (
        '<table style="width:100%;border-collapse:collapse;margin:12px 0;">'
        '<thead><tr style="background:#fef3c7;">'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">#</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Action Item</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Owner</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Due Date</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Priority</th>'
        '<th style="padding:8px 12px;border:1px solid #e2e8f0;">Context</th>'
        '</tr></thead>'
        f'<tbody>{action_rows if action_rows else "<tr><td colspan=6 style=padding:12px;text-align:center;>No action items identified</td></tr>"}</tbody></table>'
    )

    return (
        _section_header("6. Minutes of Meeting (MOM)")
        + f'<p><strong>Date:</strong> {date} &nbsp;|&nbsp; '
        + f'<strong>Attendees:</strong> {_esc(", ".join(attendees) or "Unknown")}</p>'
        + "<h3 style='margin:16px 0 6px;font-size:15px;color:#334155;'>Agenda Items Discussed</h3>"
        + agenda_table
        + "<h3 style='margin:16px 0 6px;font-size:15px;color:#334155;'>📋 Action Items</h3>"
        + action_table
    )


def _render_actionable_insights(data: dict) -> str:
    insights = data.get("actionable_insights") or []
    return (
        _section_header("7. Actionable Insights")
        + _ul(insights)
    )


def _render_key_flags(data: dict) -> str:
    kf = data.get("key_flags", {})
    has_any = any([
        kf.get("low_engagement"),
        kf.get("dominating_speakers"),
        kf.get("off_topic_periods"),
        kf.get("inefficient_time"),
        kf.get("notes"),
    ])
    if not has_any:
        return (
            _section_header("8. Key Flags")
            + '<p style="color:#22c55e;">✅ No significant flags raised.</p>'
        )

    blocks = ""
    if kf.get("low_engagement"):
        blocks += "<strong>⚠ Low Engagement:</strong>" + _ul(kf["low_engagement"])
    if kf.get("dominating_speakers"):
        blocks += "<strong>⚠ Dominating Speakers:</strong>" + _ul(kf["dominating_speakers"])
    if kf.get("off_topic_periods"):
        blocks += "<strong>🔴 Off-Topic Periods:</strong>" + _ul(kf["off_topic_periods"])
    if kf.get("inefficient_time"):
        blocks += "<strong>⏱ Inefficient Time Usage:</strong>" + _ul(kf["inefficient_time"])
    if kf.get("notes"):
        blocks += f'<p><strong>Notes:</strong> {_esc(kf["notes"])}</p>'

    return _section_header("8. Key Flags") + blocks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def format_email_html(email_data: dict, meeting_meta: dict | None = None) -> str:
    """Render *email_data* (LLM JSON output) as a complete HTML email body.

    Args:
        email_data:   Parsed JSON dict returned by the LLM.
        meeting_meta: Optional dict with meeting_id, platform, date, total_cycles.

    Returns:
        Full HTML string ready to be embedded in a MIME multipart email.
    """
    meta = meeting_meta or {}
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    header = (
        '<div style="background:#1e293b;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;">'
        '<h1 style="margin:0;font-size:22px;">📊 Meeting Intelligence Report</h1>'
        f'<p style="margin:6px 0 0;font-size:13px;opacity:0.8;">'
        f'Meeting: {_esc(meta.get("meeting_id", "—"))} &nbsp;|&nbsp; '
        f'Platform: {_esc(meta.get("platform", "—"))} &nbsp;|&nbsp; '
        f'Date: {_esc(meta.get("date", "—"))} &nbsp;|&nbsp; '
        f'Cycles: {_esc(meta.get("total_cycles", "—"))}'
        f'</p></div>'
    )

    body = (
        _render_executive_summary(email_data)
        + _render_participant_contributions(email_data)
        + _render_efficiency_score(email_data)
        + _render_redundancy(email_data)
        + _render_progress_tracking(email_data)
        + _render_mom(email_data)
        + _render_actionable_insights(email_data)
        + _render_key_flags(email_data)
    )

    footer = (
        f'<p style="margin-top:32px;font-size:12px;color:#94a3b8;border-top:1px solid #e2e8f0;'
        f'padding-top:12px;">Generated by Meeting Focus Tracker · {generated_at}</p>'
    )

    return (
        '<!DOCTYPE html><html><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '</head><body style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:900px;'
        'margin:0 auto;padding:20px;color:#334155;background:#f8fafc;">'
        f'<div style="background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);'
        f'padding:0 0 24px;">'
        + header
        + f'<div style="padding:0 24px;">{body}{footer}</div>'
        + "</div></body></html>"
    )


def format_email_text(email_data: dict, meeting_meta: dict | None = None) -> str:
    """Render *email_data* as a plain-text fallback for email clients that don't support HTML.

    Returns:
        Plain-text string.
    """
    meta = meeting_meta or {}
    lines: list[str] = []

    def h(title: str) -> None:
        lines.append("")
        lines.append("=" * 60)
        lines.append(title.upper())
        lines.append("=" * 60)

    def ul(items: list) -> None:
        for it in items or []:
            lines.append(f"  • {it}")

    h("Meeting Intelligence Report")
    lines.append(f"Meeting : {meta.get('meeting_id', '—')}")
    lines.append(f"Platform: {meta.get('platform', '—')}")
    lines.append(f"Date    : {meta.get('date', '—')}")
    lines.append(f"Cycles  : {meta.get('total_cycles', '—')}")

    # --- Executive Summary ---
    es = email_data.get("executive_summary", {})
    h("1. Executive Summary")
    lines.append(es.get("overview", "Insufficient data"))
    productive = es.get("productive")
    lines.append(f"Productive: {'Yes' if productive else 'No'}")
    lines.append("Key Outcomes:")
    ul(es.get("key_outcomes") or [])

    # --- Participants ---
    h("2. Participant Contribution Analysis")
    for p in email_data.get("participant_contributions") or []:
        lines.append(
            f"  {p.get('name','?')} | {p.get('participation_level','?')} | "
            f"{p.get('contribution_type','?')} | {p.get('word_count',0)} words "
            f"({p.get('word_share_pct',0)}%)"
        )
        if p.get("notable_inputs"):
            lines.append(f"    → {p['notable_inputs']}")
        if p.get("engagement_flag"):
            lines.append(f"    ⚠ {p['engagement_flag']}")

    # --- Efficiency Score ---
    eff = email_data.get("efficiency_score", {})
    h("3. Meeting Efficiency Score")
    lines.append(f"Score: {eff.get('score', 0)}/100")
    bd = eff.get("breakdown", {})
    for k, v in bd.items():
        lines.append(f"  {k.replace('_', ' ').title()}: {v}/25")
    lines.append(eff.get("justification", ""))

    # --- Redundancy ---
    red = email_data.get("redundancy_analysis", {})
    h("4. Redundancy & Repetition Analysis")
    lines.append(f"Added New Value: {'Yes' if red.get('added_new_value') else 'No'}")
    lines.append(red.get("summary", "Insufficient data"))
    lines.append("Repeated Topics:")
    ul(red.get("repeated_topics") or [])
    lines.append(f"History: {red.get('compared_to_history', 'No previous meeting data')}")

    # --- Progress Tracking ---
    pt = email_data.get("progress_tracking", {})
    h("5. Progress Tracking")
    lines.append(f"Status: {pt.get('status', 'unknown').upper()}")
    lines.append(pt.get("comparison_note", "First meeting in this series"))
    lines.append("Moved Forward:")
    ul(pt.get("moved_forward") or [])
    lines.append("Remained Stuck:")
    ul(pt.get("remained_stuck") or [])
    lines.append("Repeated Without Progress:")
    ul(pt.get("repeated_without_progress") or [])

    # --- MOM ---
    mom = email_data.get("minutes_of_meeting", {})
    h("6. Minutes of Meeting (MOM)")
    lines.append(f"Date     : {mom.get('date', 'Unknown')}")
    lines.append(f"Attendees: {', '.join(mom.get('attendees') or [])}")
    lines.append("")
    lines.append("Agenda Items:")
    for item in mom.get("agenda_items_covered") or []:
        lines.append(
            f"  {item.get('item_number','?')}. {item.get('title','?')} "
            f"[{item.get('outcome','?').upper()}]"
        )
        lines.append(f"     {item.get('discussion_summary','')}")
        for d in item.get("decisions") or []:
            lines.append(f"     Decision: {d}")
    lines.append("")
    lines.append("Action Items:")
    for idx, act in enumerate(mom.get("action_items") or [], 1):
        lines.append(
            f"  {idx}. [{act.get('priority','?').upper()}] {act.get('action','?')}"
        )
        lines.append(
            f"     Owner: {act.get('owner','?')}  |  Due: {act.get('due_date','Not specified')}"
        )
        if act.get("context"):
            lines.append(f"     Context: {act['context']}")

    # --- Insights ---
    h("7. Actionable Insights")
    ul(email_data.get("actionable_insights") or [])

    # --- Flags ---
    kf = email_data.get("key_flags", {})
    h("8. Key Flags")
    if kf.get("low_engagement"):
        lines.append("Low Engagement:")
        ul(kf["low_engagement"])
    if kf.get("dominating_speakers"):
        lines.append("Dominating Speakers:")
        ul(kf["dominating_speakers"])
    if kf.get("off_topic_periods"):
        lines.append("Off-Topic Periods:")
        ul(kf["off_topic_periods"])
    if kf.get("inefficient_time"):
        lines.append("Inefficient Time Usage:")
        ul(kf["inefficient_time"])
    if kf.get("notes"):
        lines.append(f"Notes: {kf['notes']}")
    if not any([kf.get(k) for k in ("low_engagement", "dominating_speakers",
                                     "off_topic_periods", "inefficient_time", "notes")]):
        lines.append("No significant flags raised.")

    lines.append("")
    lines.append("─" * 60)
    lines.append("Generated by Meeting Focus Tracker")

    return "\n".join(lines)
