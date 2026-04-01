# Meeting Intelligence Assistant — Production Rollout Plan
### Organisation: 200 People | Prepared: April 2026

---

## Executive Summary

The Meeting Intelligence Assistant automatically joins every Google Meet scheduled
in the company calendar, tracks whether discussions stay on agenda, and emails a
16-section professional intelligence report to all attendees the moment a meeting
ends. Rolling it out to 200 people is a 6-week phased process requiring zero
per-user installation — the bot joins on its own, the email lands automatically.

---

## 1. Pre-Rollout: Infrastructure Setup (Week 0)

### 1.1 Choose a Hosting Environment

| Option | Best For | Recommended? |
|--------|----------|--------------|
| **AWS EC2 t3.small** | Long-running auto mode | ✅ Yes |
| **Google Cloud Run** | Serverless, scale-to-zero | ⚠️ Complex (persistent process) |
| **Railway / Render** | Hackathon / small orgs | ⚠️ Limited for production |
| **On-premise VM** | Air-gapped environments | ✅ Yes |

**Recommendation:** AWS EC2 `t3.small` (2 vCPU, 2GB RAM) — $15/month.
The app runs a single persistent Python process, so a long-running VM is the
right fit. For larger scale (100+ concurrent meetings) upgrade to `t3.medium`.

### 1.2 Required Accounts & API Keys

| Service | Purpose | Action Required |
|---------|---------|----------------|
| **Vexa.ai** | Meeting bot that joins calls | Sign up at vexa.ai, get API key |
| **Groq** | LLM inference (llama-3.3-70b) | Sign up at console.groq.com, get API key |
| **Google Cloud Console** | OAuth for Calendar + Gmail | Create OAuth 2.0 credentials (existing setup reusable) |
| **AWS/GCP** | VM hosting | Create instance |

### 1.3 Secrets Management

```
DO NOT store API keys in .env files on production servers.
```

Use **AWS Secrets Manager** or **HashiCorp Vault**:

```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret --name meeting-tracker/prod \
  --secret-string '{
    "VEXA_API_KEY": "...",
    "LLM_API_KEY": "...",
    "GOOGLE_CREDENTIALS": "..."
  }'
```

Inject into environment at process startup via an IAM role — no secrets on disk.

### 1.4 Google OAuth — Service Account Setup (Critical for Prod)

The current setup uses a personal `token.json` (expires every hour, needs browser
re-auth). For production you need a **Google Service Account** with domain-wide
delegation — no browser, no token expiry.

**Steps:**
1. Go to Google Cloud Console → IAM → Service Accounts → Create
2. Enable domain-wide delegation
3. In Google Admin Console → Security → API Controls → Domain-wide delegation
4. Add the service account with these scopes:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
5. Download service account JSON key
6. Replace `credentials.json` + `token.json` with service account auth

This is the **most critical change** for production — without it the bot stops
working every hour when the OAuth token expires.

---

## 2. Rollout Phases

### Phase 1 — Internal Pilot (Week 1–2) | Target: 10–15 People

**Who:** Engineering team + product manager.

**Checklist:**
- [ ] Deploy on EC2, verify bot joins meetings automatically
- [ ] Run 5 real meetings, review email reports
- [ ] Verify thread grouping (recurring standup should link to same thread)
- [ ] Confirm Gmail API sends to all attendees (no SMTP config needed)
- [ ] Validate empty-meeting threshold doesn't false-trigger (90s minimum)
- [ ] Test bot-kicked scenario (manually remove bot, confirm email sends)
- [ ] Collect feedback on report quality (16 sections)

**Success Criteria:**
- Bot joins 100% of scheduled meetings within 5 minutes of start
- Email delivered to all attendees within 3 minutes of meeting end
- Zero false "meeting empty" exits during active meetings
- 0 crashes over 5 business days

**Rollback Plan:** Remove the bot from Google Calendar integration, app stops
joining meetings. Zero impact on existing tools.

---

### Phase 2 — Department Rollout (Week 3–4) | Target: 50 People

**Who:** Engineering + Product + Sales (3 departments).

**Changes from Phase 1:**
- Switch to Service Account auth (no more manual token refresh)
- Enable Slack notifications for focus deviations (optional)
- Set up a shared `#meeting-summaries` Slack channel for report links
- Configure `DEVIATION_THRESHOLD` and `ALERT_COOLDOWN` per team preference

**Monitoring Setup:**
```bash
# Set up CloudWatch alerts for:
# - Process crashes (auto-restart with systemd)
# - API error rate > 5%
# - Email delivery failures
```

**Systemd service for auto-restart:**
```ini
[Unit]
Description=Meeting Focus Tracker
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/meeting-tracker
ExecStart=/usr/bin/python3 main.py --auto
Restart=always
RestartSec=10
EnvironmentFile=/opt/meeting-tracker/.env.prod

[Install]
WantedBy=multi-user.target
```

**Success Criteria:**
- 50 people using, >80% positive feedback on report usefulness
- Support tickets < 2 per week

---

### Phase 3 — Full Org Rollout (Week 5–6) | Target: 200 People

**Who:** All departments including HR, Finance, Operations.

**Additional Changes:**
- Upgrade EC2 to `t3.medium` if >20 concurrent meetings observed
- Set up meeting history dashboard (use existing `query.py` as backend)
- Brief 30-min "how to read your meeting report" training per department
- Add FAQ / runbook to internal wiki

**Ongoing Operations:**
- Weekly review of thread groupings (are similar meetings linking correctly?)
- Monthly Groq API spend review
- Quarterly Google OAuth credentials rotation

---

## 3. Configuration Changes Required Per Environment

### 3.1 .env.prod (Production)

```bash
# Core
LLM_API_KEY=<from-secrets-manager>
LLM_API_BASE=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
VEXA_API_KEY=<from-secrets-manager>
VEXA_API_BASE=https://api.cloud.vexa.ai
MEETING_PLATFORM=google_meet

# Timing — tuned for real meetings
POLL_INTERVAL_SECONDS=30
DEVIATION_THRESHOLD=2
ALERT_COOLDOWN_SECONDS=120

# Google (use service account in prod, not personal OAuth)
ENABLE_GOOGLE_CALENDAR=true
ENABLE_GOOGLE_GMAIL=true
ENABLE_GOOGLE_DRIVE=false
GOOGLE_CREDENTIALS_FILE=/secrets/service-account.json
GOOGLE_CALENDAR_ID=primary

# Agenda enforcement
REQUIRE_AGENDA_VALIDATION=true
AGENDA_MIN_QUALITY=fair
```

### 3.2 Changes to Code for Production

| Change | File | Priority |
|--------|------|----------|
| Service account auth (no token.json) | `services/google_auth.py` | 🔴 Critical |
| Pull previous meetings from thread (not just meeting_id) | `tracker.py` | 🟡 High |
| Rate limit retry with exponential backoff | `services/llm_client.py` | 🟡 High |
| Structured logging to file / CloudWatch | `main.py` | 🟡 High |
| Health check endpoint (HTTP GET /health) | `main.py` | 🟢 Nice to have |
| Slack alert on bot failure | `services/calendar_watcher.py` | 🟢 Nice to have |

---

## 4. Tools Stack

| Layer | Tool | Why |
|-------|------|-----|
| Hosting | AWS EC2 t3.small | Simple, persistent process, $15/mo |
| Secrets | AWS Secrets Manager | No secrets on disk |
| Process management | systemd | Auto-restart on crash |
| Monitoring | AWS CloudWatch | Logs + crash alerts |
| Google auth | Service Account (domain-wide) | No token expiry |
| LLM | Groq (llama-3.3-70b-versatile) | Fast, cheap, good JSON output |
| Meeting bot | Vexa.ai | Google Meet + Zoom + Teams support |
| Email | Gmail API (OAuth) | Already integrated, zero config per user |
| Storage | Local disk (JSON + threads/) | Simple, no DB needed at 200 users |
| CI/CD | GitHub Actions → SSH deploy | Auto-deploy on merge to main |

---

## 5. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Groq rate limit during peak hours | Medium | Report delayed | Exponential backoff + retry queue |
| Vexa bot not admitted to meeting | High | No transcript | Alert user to admit FocusBot in Meet |
| OAuth token expires (current setup) | High | Bot stops | Switch to Service Account auth |
| False meeting-empty exit | Low (fixed) | Report sent early | 90s threshold + transcript-first logic |
| LLM returns malformed JSON | Low (70b model) | Report skipped | 3-retry logic already in llm_client.py |
| Meeting with no agenda | Medium | Poor report | Agenda validation enforced (REQUIRE_AGENDA_VALIDATION=true) |

---

## 6. Success Metrics (30-Day Post-Rollout)

- **Bot join rate:** >95% of calendar meetings joined successfully
- **Email delivery rate:** >99% of meetings produce and send a report
- **False exits:** <1% of meetings get an early exit (meeting still active)
- **User satisfaction:** >4/5 in monthly survey on report usefulness
- **Mean time to report:** <3 minutes after meeting ends
- **Thread accuracy:** >80% of recurring meetings correctly linked to same thread
