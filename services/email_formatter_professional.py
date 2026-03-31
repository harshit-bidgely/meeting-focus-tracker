"""Professional-grade email formatter with executive styling.

Transforms comprehensive meeting intelligence JSON into beautifully formatted
HTML and plain-text emails suitable for C-suite, managers, and HR departments.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone


def _esc(value: object) -> str:
    """HTML-escape a value."""
    return html.escape(str(value) if value is not None else "")


def _gauge(score: int, label: str = "") -> str:
    """Create a visual score gauge (0-100)."""
    pct = max(0, min(100, score))
    if pct >= 80:
        color, status = "#10b981", "Excellent"
    elif pct >= 60:
        color, status = "#f59e0b", "Good"
    elif pct >= 40:
        color, status = "#ef5350", "Fair"
    else:
        color, status = "#c62828", "Poor"

    return (
        f'<div style="margin:8px 0;">'
        f'  <div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
        f'    <span style="font-weight:600;color:#1e293b;">{label or "Score"}</span>'
        f'    <span style="font-weight:700;color:{color};font-size:16px;">{score}/100 ({status})</span>'
        f'  </div>'
        f'  <div style="background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden;">'
        f'    <div style="background:{color};width:{pct}%;height:100%;transition:width 0.3s;"></div>'
        f'  </div>'
        f'</div>'
    )


def _section_title(title: str, subtitle: str = "") -> str:
    """Professional section title."""
    subtitle_html = f'<p style="margin:4px 0 0;color:#64748b;font-size:13px;">{_esc(subtitle)}</p>' if subtitle else ""
    return (
        f'<div style="margin:32px 0 16px;border-left:4px solid #0f172a;padding-left:16px;">'
        f'  <h2 style="margin:0;color:#0f172a;font-size:20px;font-weight:700;">{_esc(title)}</h2>'
        f'  {subtitle_html}'
        f'</div>'
    )


def _metric_card(label: str, value: str, unit: str = "") -> str:
    """Metric card for KPIs."""
    return (
        f'<div style="display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;'
        f'padding:12px 16px;margin-right:12px;margin-bottom:12px;min-width:140px;">'
        f'  <div style="color:#64748b;font-size:12px;font-weight:600;text-transform:uppercase;">{_esc(label)}</div>'
        f'  <div style="color:#0f172a;font-size:22px;font-weight:700;margin-top:4px;">'
        f'    {_esc(value)}<span style="font-size:14px;color:#64748b;margin-left:4px;">{_esc(unit)}</span>'
        f'  </div>'
        f'</div>'
    )


def _participant_card(name: str, stats: dict) -> str:
    """Detailed participant profile card."""
    level = stats.get("participation_metrics", {}).get("participation_level", "Unknown")
    words = stats.get("participation_metrics", {}).get("total_words", 0)
    share = stats.get("participation_metrics", {}).get("word_share_percent", 0)
    influence = stats.get("influence_assessment", "Unknown influence")
    style = stats.get("communication_style", {}).get("type", "contributor")

    level_color = {"High": "#10b981", "Medium": "#f59e0b", "Low": "#ef5350"}.get(level, "#6b7280")

    strengths = stats.get("strengths", "")
    strengths_html = f'<p style="margin:12px 0 0;font-size:13px;line-height:1.5;"><strong>Strengths:</strong> {_esc(strengths)}</p>' if strengths else ""

    dev_areas = stats.get("development_areas", "")
    dev_html = f'<p style="margin:8px 0 0;font-size:13px;line-height:1.5;"><strong>Growth Area:</strong> {_esc(dev_areas)}</p>' if dev_areas else ""

    return (
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;'
        f'margin-bottom:12px;page-break-inside:avoid;">'
        f'  <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px;">'
        f'    <div>'
        f'      <h4 style="margin:0;color:#0f172a;font-size:16px;font-weight:700;">{_esc(name)}</h4>'
        f'      <p style="margin:4px 0 0;color:#64748b;font-size:13px;">{_esc(style)} • {_esc(influence)}</p>'
        f'    </div>'
        f'    <span style="background:{level_color};color:#fff;padding:4px 10px;border-radius:4px;'
        f'font-size:12px;font-weight:600;">{_esc(level)}</span>'
        f'  </div>'
        f'  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'    <div><span style="color:#64748b;font-size:12px;">Words Spoken:</span>'
        f'      <div style="color:#0f172a;font-size:16px;font-weight:600;margin-top:2px;">{words} ({share}%)</div>'
        f'    </div>'
        f'    <div><span style="color:#64748b;font-size:12px;">Speaking Style:</span>'
        f'      <div style="color:#0f172a;font-size:13px;margin-top:2px;">{_esc(stats.get("communication_style", {}).get("confidence_level", "Unknown"))} confidence</div>'
        f'    </div>'
        f'  </div>'
        f'  {strengths_html}'
        f'  {dev_html}'
        f'</div>'
    )


def _risk_card(risk: dict) -> str:
    """Risk assessment card."""
    impact_color = {"high": "#c62828", "medium": "#f57c00", "low": "#fbc02d"}.get(
        risk.get("probability", "medium").lower(), "#6b7280"
    )

    return (
        f'<div style="background:#fff5f5;border-left:4px solid {impact_color};padding:12px 16px;'
        f'margin-bottom:12px;border-radius:4px;">'
        f'  <h5 style="margin:0 0 8px;color:#0f172a;font-weight:700;font-size:14px;">'
        f'    ⚠️ {_esc(risk.get("risk", "Unknown Risk"))}'
        f'  </h5>'
        f'  <p style="margin:0 0 8px;font-size:13px;color:#64748b;"><strong>Impact:</strong> {_esc(risk.get("impact", ""))}</p>'
        f'  <p style="margin:0 0 8px;font-size:13px;color:#64748b;"><strong>Probability:</strong> <span style="color:{impact_color};font-weight:600;">{_esc(risk.get("probability", "").upper())}</span></p>'
        f'  <p style="margin:0;font-size:13px;color:#64748b;"><strong>Mitigation:</strong> {_esc(risk.get("mitigation", ""))}</p>'
        f'</div>'
    )


def _action_item_card(idx: int, action: dict) -> str:
    """Professional action item card."""
    priority_colors = {
        "critical": "#c62828",
        "high": "#f57c00",
        "medium": "#fbc02d",
        "low": "#689f38"
    }
    pri_color = priority_colors.get(action.get("priority", "medium").lower(), "#6b7280")

    return (
        f'<div style="background:#f8fafc;border:1px solid #cbd5e1;border-radius:6px;padding:14px;'
        f'margin-bottom:12px;page-break-inside:avoid;">'
        f'  <div style="display:flex;justify-content:space-between;align-items:start;">'
        f'    <div style="flex:1;">'
        f'      <h5 style="margin:0 0 8px;color:#0f172a;font-size:14px;font-weight:700;">'
        f'        [{idx}] {_esc(action.get("action", ""))}'
        f'      </h5>'
        f'      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px;'
        f'margin:8px 0;color:#64748b;">'
        f'        <div><strong>Owner:</strong> {_esc(action.get("owner", "Unassigned"))}</div>'
        f'        <div><strong>Due:</strong> {_esc(action.get("due_date", "Not specified"))}</div>'
        f'        <div><strong>Impact:</strong> {_esc(action.get("business_impact", ""))}</div>'
        f'        <div><strong>Effort:</strong> {_esc(action.get("estimated_effort", ""))}</div>'
        f'      </div>'
        f'      <p style="margin:8px 0 0;font-size:12px;color:#475569;line-height:1.5;">'
        f'        {_esc(action.get("context", ""))}'
        f'      </p>'
        f'    </div>'
        f'    <span style="background:{pri_color};color:#fff;padding:6px 12px;border-radius:4px;'
        f'font-size:11px;font-weight:700;white-space:nowrap;margin-left:12px;">'
        f'      {_esc(action.get("priority", "medium").upper())}'
        f'    </span>'
        f'  </div>'
        f'</div>'
    )


def format_professional_html(data: dict, meeting_meta: dict | None = None) -> str:
    """Generate comprehensive professional HTML email."""
    meta = meeting_meta or {}
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    overview = data.get("meeting_overview", {})
    metrics = data.get("key_metrics", {})

    # Build participant sections
    participants_html = ""
    for p in data.get("participant_deep_analysis", []):
        participants_html += _participant_card(p.get("name", "Unknown"), p)

    # Build risk sections
    risks_html = ""
    for risk in data.get("risk_assessment", {}).get("critical_risks", []):
        risks_html += _risk_card(risk)

    # Build action items
    actions_html = ""
    for idx, action in enumerate(data.get("action_items", []), 1):
        actions_html += _action_item_card(idx, action)

    # Build decisions
    decisions_html = ""
    for d in data.get("detailed_decisions", []):
        decisions_html += (
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:14px;margin-bottom:12px;">'
            f'  <h5 style="margin:0 0 8px;color:#0f172a;font-weight:700;font-size:14px;">'
            f'    [{_esc(d.get("decision_id", "?"))}] {_esc(d.get("decision", ""))}'
            f'  </h5>'
            f'  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px;color:#64748b;margin:8px 0;">'
            f'    <div><strong>Decision Maker:</strong> {_esc(d.get("who_decided", "Unknown"))}</div>'
            f'    <div><strong>Consensus:</strong> {_esc(d.get("consensus_level", "Unknown"))}</div>'
            f'    <div><strong>Timeline:</strong> {_esc(d.get("timeline", "Not specified"))}</div>'
            f'    <div><strong>Status:</strong> {_esc(d.get("implementation_readiness", "Unknown"))}</div>'
            f'  </div>'
            f'  <p style="margin:8px 0 0;font-size:12px;color:#475569;"><strong>Context:</strong> {_esc(d.get("context", ""))}</p>'
            f'</div>'
        )

    # Build opportunities
    opportunities_html = ""
    for o in data.get("opportunities", []):
        opportunities_html += (
            f'<div style="background:#f0fdf4;border-left:4px solid #10b981;padding:14px;margin-bottom:12px;border-radius:4px;">'
            f'  <h5 style="margin:0 0 8px;color:#047857;font-weight:700;">💡 {_esc(o.get("opportunity", ""))}</h5>'
            f'  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px;color:#374151;margin:8px 0;">'
            f'    <div><strong>Upside:</strong> {_esc(o.get("upside", ""))}</div>'
            f'    <div><strong>Effort:</strong> {_esc(o.get("effort_estimate", ""))}</div>'
            f'  </div>'
            f'</div>'
        )

    # HR insights
    hr_insights = data.get("hr_insights", {})

    # Trend section
    trend_html = ""
    if metrics.get("trend_vs_previous_5_meetings"):
        trend_data = metrics.get("trend_vs_previous_5_meetings", {})
        trend_html = (
            f'<div style="background:#f0fdf4;border-left:4px solid #10b981;padding:16px;margin:16px 0;border-radius:4px;">'
            f'  <strong style="color:#047857;">📈 Trend Analysis:</strong>'
            f'  <p style="margin:8px 0 0;color:#374151;font-size:13px;">'
            f'    {_esc(trend_data.get("note", ""))} - '
            f'    Currently {_esc(trend_data.get("pattern", "stable"))}'
            f'  </p>'
            f'</div>'
        )

    # Critical/high priority count
    critical_high_count = len([a for a in data.get("action_items", []) if a.get("priority") in ["critical", "high"]])

    # Build the full HTML
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Meeting Intelligence Report</title>
</head>
<body style="font-family:'Segoe UI',Arial,sans-serif;max-width:900px;margin:0 auto;padding:20px;color:#334155;background:#f1f5f9;line-height:1.6;">

<!-- HEADER -->
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);color:#fff;padding:32px;border-radius:8px 8px 0 0;margin-bottom:24px;">
    <h1 style="margin:0;font-size:28px;font-weight:700;margin-bottom:8px;">📊 Meeting Intelligence Report</h1>
    <p style="margin:0;opacity:0.9;font-size:15px;">{_esc(overview.get("title", "Professional Meeting Analysis"))}</p>
    <div style="margin-top:16px;border-top:1px solid rgba(255,255,255,0.2);padding-top:12px;display:flex;gap:24px;font-size:13px;">
        <div><strong>Date:</strong> {_esc(overview.get("date", "Unknown"))}</div>
        <div><strong>Participants:</strong> {_esc(overview.get("participants_count", "Unknown"))}</div>
        <div><strong>Duration:</strong> {_esc(overview.get("duration_minutes", "Unknown"))} min</div>
        <div><strong>Health:</strong> {_esc(overview.get("meeting_health", "Unknown"))}</div>
    </div>
</div>

<!-- EXECUTIVE SUMMARY -->
{_section_title("Executive Summary", "Key Decisions, Outcomes & Implications")}
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:16px;margin:16px 0;">
    <p style="margin:0;color:#475569;font-size:14px;line-height:1.7;">{_esc(overview.get("narrative", ""))}</p>
</div>

<!-- KEY METRICS -->
{_section_title("Key Performance Indicators", "Meeting Quality & Health Scorecard")}
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:20px;margin:16px 0;">
    <div style="margin-bottom:16px;">
        {_gauge(metrics.get("overall_meeting_score", 0), "Overall Meeting Score")}
    </div>
    <div style="margin:16px 0;font-size:13px;color:#64748b;">
        <strong style="color:#0f172a;">Health Indicators:</strong>
    </div>
    <div>
        {_metric_card("Agenda Adherence", str(metrics.get("meeting_health_indicators", {}).get("agenda_adherence", 0)), "%")}
        {_metric_card("Decision Velocity", str(metrics.get("meeting_health_indicators", {}).get("decision_velocity", 0)), "%")}
        {_metric_card("Team Engagement", str(metrics.get("meeting_health_indicators", {}).get("team_engagement", 0)), "%")}
        {_metric_card("Psychological Safety", str(metrics.get("meeting_health_indicators", {}).get("psychological_safety", 0)), "%")}
        {_metric_card("Time Efficiency", str(metrics.get("meeting_health_indicators", {}).get("time_efficiency", 0)), "%")}
        {_metric_card("Meeting Value", "High" if metrics.get("overall_meeting_score", 0) > 70 else "Medium", "")}
    </div>
</div>

<!-- TREND COMPARISON -->
{trend_html}

<!-- PARTICIPANT ANALYSIS -->
{_section_title("Participant Deep Analysis", "Individual Contributions, Styles & Growth")}
<p style="color:#64748b;font-size:13px;margin:0 0 16px;">Detailed breakdown of each participant's role, engagement level, communication style, and development opportunities.</p>
{participants_html}

<!-- TEAM DYNAMICS -->
{_section_title("Team Dynamics & Collaboration", "Health, Safety & Working Relationships")}
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:16px;margin:16px 0;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
        {_gauge(data.get("team_dynamics", {}).get("collaboration_score", 0), "Team Collaboration")}
        {_gauge(data.get("hr_insights", {}).get("team_health_score", 0), "Team Health")}
    </div>
</div>

<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:16px;margin:16px 0;">
    <h4 style="margin:0 0 12px;color:#0f172a;">🔍 Key Observations:</h4>
    <ul style="margin:0;padding-left:20px;color:#475569;font-size:13px;">
        <li style="margin-bottom:8px;"><strong>Psychological Safety:</strong> {_esc(data.get("team_dynamics", {}).get("psychological_safety_indicators", "Unknown"))}</li>
        <li style="margin-bottom:8px;"><strong>Balance:</strong> {_esc("Balanced participation" if data.get("team_dynamics", {}).get("dominance_patterns", {}).get("balanced") else "Imbalanced - some voices dominate")}</li>
        <li style="margin-bottom:8px;"><strong>Consensus:</strong> {_esc(data.get("team_dynamics", {}).get("agreement_level", "Unknown"))}</li>
        <li><strong>Power Dynamics:</strong> {_esc(data.get("team_dynamics", {}).get("power_dynamics", "Balanced"))}</li>
    </ul>
</div>

<!-- DECISIONS MADE -->
{_section_title("Decisions Made", "Critical Decisions & Implementation Readiness")}
{decisions_html if decisions_html else '<p style="color:#64748b;font-size:13px;">No decisions documented in this meeting.</p>'}

<!-- RISKS & BLOCKERS -->
{_section_title("Risk Assessment & Blockers", "Critical Threats & Mitigation")}
{risks_html if risks_html else '<p style="color:#10b981;font-weight:600;">✅ No critical risks identified</p>'}

<!-- OPPORTUNITIES -->
{_section_title("Strategic Opportunities", "Growth Areas & Value Creation")}
{opportunities_html if opportunities_html else '<p style="color:#64748b;font-size:13px;">No strategic opportunities identified.</p>'}

<!-- HR INSIGHTS -->
{_section_title("HR & Organizational Insights", "Engagement, Inclusion & Retention")}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0;">
    {_gauge(hr_insights.get("team_health_score", 0), "Team Health")}
    {_metric_card("Engagement", hr_insights.get("engagement_level", "Unknown").title(), "")}
</div>

<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:16px;margin:16px 0;">
    <h4 style="margin:0 0 12px;color:#0f172a;">👥 Key HR Observations:</h4>
    <ul style="margin:0;padding-left:20px;color:#475569;font-size:13px;">
        <li style="margin-bottom:8px;"><strong>Inclusion:</strong> {_esc(hr_insights.get("inclusion_assessment", {}).get("participation_diversity", "Unknown"))}</li>
        <li style="margin-bottom:8px;"><strong>Safety:</strong> {_esc(hr_insights.get("inclusion_assessment", {}).get("psychological_safety", "Unknown"))} psychological safety</li>
        <li style="margin-bottom:8px;"><strong>Collaboration:</strong> {_esc(hr_insights.get("collaboration_health", "Unknown"))}</li>
        <li><strong>Skills:</strong> {_esc(hr_insights.get("capability_assessment", "Sufficient capabilities present"))}</li>
    </ul>
</div>

<!-- ACTION ITEMS -->
{_section_title("Action Items & Next Steps", "Owners, Timelines & Success Criteria")}
<div style="background:#fffbeb;border-left:4px solid #f59e0b;padding:12px 16px;margin-bottom:16px;border-radius:4px;">
    <strong style="color:#92400e;">⚡ {critical_high_count} Critical/High Priority Items</strong>
</div>
{actions_html if actions_html else '<p style="color:#64748b;font-size:13px;">No action items documented.</p>'}

<!-- FOOTER -->
<div style="margin-top:40px;border-top:1px solid #e2e8f0;padding-top:20px;color:#64748b;font-size:12px;">
    <p style="margin:0 0 8px;">Generated: {generated_at}</p>
    <p style="margin:0;">Meeting Focus Tracker • Professional Intelligence Analysis</p>
</div>

</body>
</html>"""

    return html_content


def format_professional_text(data: dict, meeting_meta: dict | None = None) -> str:
    """Generate plain-text version of professional report."""
    overview = data.get("meeting_overview", {})
    metrics = data.get("key_metrics", {})

    lines = [
        "=" * 80,
        "MEETING INTELLIGENCE REPORT",
        "=" * 80,
        "",
        f"Title: {overview.get('title', 'Professional Meeting Analysis')}",
        f"Date: {overview.get('date', 'Unknown')}",
        f"Participants: {overview.get('participants_count', 'Unknown')}",
        f"Duration: {overview.get('duration_minutes', 'Unknown')} minutes",
        f"Meeting Health: {overview.get('meeting_health', 'Unknown')}",
        "",
        "EXECUTIVE SUMMARY",
        "-" * 40,
        overview.get("narrative", ""),
        "",
        "KEY METRICS",
        "-" * 40,
        f"Overall Score: {metrics.get('overall_meeting_score', 0)}/100",
        f"  - Agenda Adherence: {metrics.get('meeting_health_indicators', {}).get('agenda_adherence', 0)}%",
        f"  - Decision Velocity: {metrics.get('meeting_health_indicators', {}).get('decision_velocity', 0)}%",
        f"  - Team Engagement: {metrics.get('meeting_health_indicators', {}).get('team_engagement', 0)}%",
        f"  - Psychological Safety: {metrics.get('meeting_health_indicators', {}).get('psychological_safety', 0)}%",
        f"  - Time Efficiency: {metrics.get('meeting_health_indicators', {}).get('time_efficiency', 0)}%",
        "",
        "PARTICIPANTS",
        "-" * 40,
    ]

    for p in data.get("participant_deep_analysis", []):
        lines.append(f"\n{p.get('name', 'Unknown')}:")
        metrics_p = p.get("participation_metrics", {})
        lines.append(f"  - Words Spoken: {metrics_p.get('total_words', 0)} ({metrics_p.get('word_share_percent', 0)}%)")
        lines.append(f"  - Participation Level: {metrics_p.get('participation_level', 'Unknown')}")
        style = p.get("communication_style", {})
        lines.append(f"  - Style: {style.get('type', 'Unknown')} ({style.get('confidence_level', 'Unknown')} confidence)")
        lines.append(f"  - Influence: {p.get('influence_assessment', 'Unknown')}")
        if p.get("strengths"):
            lines.append(f"  - Strengths: {p.get('strengths')}")
        if p.get("development_areas"):
            lines.append(f"  - Growth Areas: {p.get('development_areas')}")

    lines.extend([
        "",
        "ACTION ITEMS",
        "-" * 40,
    ])

    for idx, action in enumerate(data.get("action_items", []), 1):
        lines.append(f"\n[{idx}] {action.get('action', '')}")
        lines.append(f"    Owner: {action.get('owner', 'Unassigned')}")
        lines.append(f"    Due: {action.get('due_date', 'Not specified')}")
        lines.append(f"    Priority: {action.get('priority', 'medium').upper()}")
        lines.append(f"    Impact: {action.get('business_impact', '')}")

    if data.get("risk_assessment", {}).get("critical_risks"):
        lines.extend([
            "",
            "RISKS & MITIGATIONS",
            "-" * 40,
        ])
        for risk in data.get("risk_assessment", {}).get("critical_risks", []):
            lines.append(f"\n⚠️ {risk.get('risk', 'Unknown Risk')}")
            lines.append(f"   Impact: {risk.get('impact', '')}")
            lines.append(f"   Probability: {risk.get('probability', 'Unknown')}")
            lines.append(f"   Mitigation: {risk.get('mitigation', '')}")

    lines.extend([
        "",
        "=" * 80,
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 80,
    ])

    return "\n".join(lines)
