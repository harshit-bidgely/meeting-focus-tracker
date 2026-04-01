# Meeting Intelligence Assistant — Detailed Cost Analysis
### Organisation: 200 People | Prepared: April 2026

---

## Section 1: Meeting Hours — Ground-Up Calculation
### Context: WFH Tech Indian Startup, 200 People

WFH Indian startups have distinct meeting patterns vs western orgs:
- **Heavy standup culture** — daily 15–20 min standups every team, every day
- **Agile-first** — sprint planning, grooming, retro every 2 weeks
- **Engineering-heavy headcount** — ~55% of org is engineers
- **IST timezone** — most meetings 10 AM–7 PM IST
- **More meetings than in-office** — no hallway conversations → video calls for everything
- **Founders extremely meeting-heavy** — investor calls, customer calls, all-hands
- **Over-communication culture** — PMs, founders, team leads are in 2-3× more meetings than western equivalents

---

### 1.1 Realistic Role Distribution for WFH Indian Tech Startup (200 People)

| Role | Headcount | % of Org |
|------|-----------|----------|
| Founders / C-suite (CEO, CTO, CPO, CFO) | 5 | 2.5% |
| VPs / Directors | 8 | 4% |
| Engineering Managers / Team Leads | 15 | 7.5% |
| Senior Engineers (SDE-2, SDE-3) | 40 | 20% |
| Engineers (SDE-1, Intern) | 60 | 30% |
| Product Managers | 15 | 7.5% |
| Designers (UI/UX) | 10 | 5% |
| Sales / Business Development | 15 | 7.5% |
| Marketing | 10 | 5% |
| HR / Talent Acquisition | 10 | 5% |
| Finance / Admin / Operations | 12 | 6% |
| **Total** | **200** | **100%** |

---

### 1.2 Meeting Breakdown Per Role — Weekly Hours

#### Founders / C-suite (5 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Investor / board calls | 2×/week | 60 min | 2.00 |
| Customer / BD calls | 3×/week | 45 min | 2.25 |
| Leadership sync | 2×/week | 60 min | 2.00 |
| All-hands preparation | 1×/week | 30 min | 0.50 |
| 1:1s with direct reports | 4×/week | 30 min | 2.00 |
| Product / tech reviews | 2×/week | 60 min | 2.00 |
| HR / hiring debriefs | 2×/week | 30 min | 1.00 |
| **Total** | | | **11.75 hrs/week** |

#### VPs / Directors (8 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Leadership sync | 2×/week | 60 min | 2.00 |
| Team standup | 5×/week | 20 min | 1.67 |
| 1:1s with direct reports | 5×/week | 30 min | 2.50 |
| Cross-functional syncs | 2×/week | 45 min | 1.50 |
| Roadmap / planning | 1×/week | 60 min | 1.00 |
| Customer calls (occasionally) | 1×/week | 45 min | 0.75 |
| **Total** | | | **9.42 hrs/week** |

#### Engineering Managers / Team Leads (15 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Daily standup (own team) | 5×/week | 20 min | 1.67 |
| Sprint planning | 1×/2 weeks | 90 min | 0.75 |
| Sprint retrospective | 1×/2 weeks | 60 min | 0.50 |
| Backlog grooming | 1×/2 weeks | 60 min | 0.50 |
| 1:1s with engineers | 4×/week | 30 min | 2.00 |
| Manager sync with VP | 1×/week | 45 min | 0.75 |
| Tech design reviews | 1×/week | 60 min | 1.00 |
| Incident / hotfix calls (avg) | 1×/week | 30 min | 0.50 |
| **Total** | | | **7.67 hrs/week** |

#### Senior Engineers / SDE-2, SDE-3 (40 people)
Context: Work in 2–3 person feature teams. Own 1 feature per quarter (3/year).
Each feature cycle drives its own meeting load on top of sprint ceremonies.

**Recurring weekly:**
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Daily standup (own team, 2–3 people) | 5×/week | 20 min | 1.67 |
| 1:1 with manager | 1×/week | 30 min | 0.50 |
| Cross-team dependency call | 2×/week | 30 min | 1.00 |
| Informal tech discussion (Slack huddle / quick call) | 3×/week | 20 min | 1.00 |
| **Weekly subtotal** | | | **4.17 hrs/week** |

**Sprint ceremonies (every 2 weeks → per-week equivalent):**
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Sprint planning (helps estimate tasks) | 1×/2 weeks | 90 min | 0.75 |
| Backlog grooming (provides tech input) | 1×/2 weeks | 60 min | 0.50 |
| Sprint retrospective | 1×/2 weeks | 60 min | 0.50 |
| Sprint demo (presents work) | 1×/2 weeks | 45 min | 0.38 |
| **Sprint subtotal** | | | **2.13 hrs/week** |

**Per-feature cycle (3 features/quarter = 1 feature/month ≈ 0.25/week):**
| Meeting Type | Per Feature | Duration | Hrs/Week Equivalent |
|-------------|-------------|----------|---------------------|
| Feature kickoff — requirements walkthrough with PM | 1 | 60 min | 0.25 |
| Tech design discussion — round 1 (architecture) | 1 | 90 min | 0.38 |
| Tech design discussion — round 2 (review + sign-off) | 1 | 60 min | 0.25 |
| API contract discussion with other team | 1 | 45 min | 0.19 |
| Mid-feature check-in / scope adjustment | 1 | 30 min | 0.13 |
| Pre-release QA discussion | 1 | 45 min | 0.19 |
| Feature demo to stakeholders | 1 | 45 min | 0.19 |
| Post-release retrospective (per feature) | 1 | 30 min | 0.13 |
| **Feature cycle subtotal** | | | **1.71 hrs/week** |

**KT (Knowledge Transfer) sessions:**
| KT Type | Frequency | Duration | Hrs/Week |
|---------|-----------|----------|----------|
| Conducting KT for new joinee / teammate on own module | 2×/month | 75 min | 0.63 |
| Receiving KT on another module / upstream dependency | 1×/month | 60 min | 0.25 |
| Tech stack / tooling KT (new framework, library) | 1×/month | 45 min | 0.19 |
| **KT subtotal** | | | **1.07 hrs/week** |

**Total SDE-2/3: 4.17 + 2.13 + 1.71 + 1.07 = 9.08 hrs/week**

---

#### Engineers / SDE-1 (60 people)
Context: Work in 2–3 person teams. Junior contributor on features.
More KT received, fewer design discussions owned.

**Recurring weekly:**
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Daily standup (own team) | 5×/week | 20 min | 1.67 |
| 1:1 with manager | 1×/week | 30 min | 0.50 |
| Cross-team dependency call (observer / participant) | 1×/week | 30 min | 0.50 |
| Informal tech discussion / pair debugging call | 3×/week | 20 min | 1.00 |
| **Weekly subtotal** | | | **3.67 hrs/week** |

**Sprint ceremonies:**
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Sprint planning | 1×/2 weeks | 90 min | 0.75 |
| Backlog grooming | 1×/2 weeks | 60 min | 0.50 |
| Sprint retrospective | 1×/2 weeks | 60 min | 0.50 |
| Sprint demo (participates, presents sub-tasks) | 1×/2 weeks | 45 min | 0.38 |
| **Sprint subtotal** | | | **2.13 hrs/week** |

**Per-feature cycle (3 features/quarter = 0.25/week):**
| Meeting Type | Per Feature | Duration | Hrs/Week Equivalent |
|-------------|-------------|----------|---------------------|
| Feature kickoff — requirements walkthrough | 1 | 60 min | 0.25 |
| Tech design discussion (participant, not owner) | 2 | 75 min avg | 0.63 |
| Mid-feature check-in | 1 | 30 min | 0.13 |
| Pre-release QA discussion | 1 | 45 min | 0.19 |
| Feature demo | 1 | 45 min | 0.19 |
| **Feature cycle subtotal** | | | **1.39 hrs/week** |

**KT sessions:**
| KT Type | Frequency | Duration | Hrs/Week |
|---------|-----------|----------|----------|
| Receiving KT from senior engineer (module onboarding) | 3×/month | 75 min | 0.94 |
| Receiving KT on new service / API owned by another team | 2×/month | 60 min | 0.50 |
| Conducting KT to pair / buddy on own small task | 1×/month | 45 min | 0.19 |
| **KT subtotal** | | | **1.63 hrs/week** |

**Total SDE-1: 3.67 + 2.13 + 1.39 + 1.63 = 8.82 hrs/week**

#### Product Managers (15 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Daily standup (attends 2 teams) | 5×/week | 15 min | 2.50 |
| Sprint planning (facilitates) | 1×/2 weeks | 90 min | 0.75 |
| Sprint retrospective | 1×/2 weeks | 60 min | 0.50 |
| Product review / demo | 1×/week | 60 min | 1.00 |
| Stakeholder alignment | 2×/week | 45 min | 1.50 |
| Customer discovery calls | 2×/week | 45 min | 1.50 |
| 1:1 with founder/VP | 1×/week | 30 min | 0.50 |
| **Total** | | | **8.25 hrs/week** |

#### Designers (10 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Daily standup | 5×/week | 15 min | 1.25 |
| Design review / critique | 2×/week | 45 min | 1.50 |
| PM-Design sync | 2×/week | 30 min | 1.00 |
| User research sessions | 1×/week | 60 min | 1.00 |
| **Total** | | | **4.75 hrs/week** |

#### Sales / Business Development (15 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Customer demo / discovery | 5×/week | 45 min | 3.75 |
| Internal sales sync | 2×/week | 30 min | 1.00 |
| Deal review with founder | 1×/week | 45 min | 0.75 |
| **Total** | | | **5.50 hrs/week** |

#### Marketing (10 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Team sync | 2×/week | 45 min | 1.50 |
| Campaign review | 1×/week | 45 min | 0.75 |
| Cross-functional (PM + Sales) | 1×/week | 30 min | 0.50 |
| **Total** | | | **2.75 hrs/week** |

#### HR / Talent Acquisition (10 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Interviews (conducting) | 6×/week | 45 min | 4.50 |
| Hiring debriefs | 3×/week | 30 min | 1.50 |
| HR sync | 1×/week | 45 min | 0.75 |
| **Total** | | | **6.75 hrs/week** |

#### Finance / Admin / Operations (12 people)
| Meeting Type | Frequency | Duration | Hrs/Week |
|-------------|-----------|----------|----------|
| Weekly ops review | 1×/week | 45 min | 0.75 |
| Finance review (monthly, spread) | 0.5×/week | 60 min | 0.50 |
| Vendor / tool review | 1×/week | 30 min | 0.50 |
| **Total** | | | **1.75 hrs/week** |

---

### 1.3 Summary — Total Org Meeting Hours Per Week

| Role | Headcount | Hrs/Week Each | Total Person-Hrs/Week |
|------|-----------|---------------|----------------------|
| Founders / C-suite | 5 | 11.75 | 58.75 |
| VPs / Directors | 8 | 9.42 | 75.36 |
| Engineering Managers / TLs | 15 | 7.67 | 115.05 |
| Senior Engineers (SDE-2/3) | 40 | **9.08** | **363.20** |
| Engineers (SDE-1) | 60 | **8.82** | **529.20** |
| Product Managers | 15 | 8.25 | 123.75 |
| Designers | 10 | 4.75 | 47.50 |
| Sales / BD | 15 | 5.50 | 82.50 |
| Marketing | 10 | 2.75 | 27.50 |
| HR / Talent | 10 | 6.75 | 67.50 |
| Finance / Admin / Ops | 12 | 1.75 | 21.00 |
| **Grand Total** | **200** | **7.95 avg** | **1,511 person-hrs/week** |

> Engineers (100 people, 50% of org) were the most underestimated group.
> When you account for **2–3 person teams + 3 features/quarter + KTs + tech discussions**,
> SDE-1 and SDE-2 each spend **~9 hrs/week** in meetings — nearly 2× the earlier estimate.
> **Overall org average: 7.95 hrs/person/week.**

---

### 1.4 Converting Person-Hours to Unique Meetings

One meeting with 3 people = 3 person-hours but **1 bot join**.
The 2–3 person team structure means meetings are smaller and more frequent.

| Metric | Calculation | Value |
|--------|-------------|-------|
| Total person-hours/week | (from table above) | 1,511 hrs |
| Blended avg meeting size | standups(3) + ceremonies(8) + tech(3) + cross-team(5) | **~4 people** |
| Blended avg meeting duration | weighted across all types | 35 min = 0.58 hr |
| Unique meetings/week | 1,511 ÷ 4 ÷ 0.58 | **~651 meetings/week** |
| Working weeks/month | 4.33 | |
| **Unique meetings/month** | 651 × 4.33 | **~2,819 meetings/month** |
| Round to | working estimate | **~2,800 meetings/month** |

> The small team size is the key driver — a 3-person standup still = 1 bot join,
> but 3 separate 2-person teams = 3 standups. With 100 engineers in ~33 small
> teams, standups alone generate **33 × 22 = 726 meetings/month**.

### 1.5 Bot-Active Meetings (After Filtering)

| Filter | Meetings Excluded | Reason |
|--------|-----------------|--------|
| Very short standups < 15 min (no agenda set) | ~560/month (20%) | Too short, bot policy |
| Pure interview sessions (HR) | ~112/month (4%) | External candidate |
| 1:1s opted out by policy | ~280/month (10%) | Privacy / personal preference |
| Informal Slack huddles (< 10 min) | ~196/month (7%) | Ad-hoc, not scheduled |
| External-only meetings | ~56/month (2%) | Organiser outside org |
| **Total excluded** | **~1,204 (43%)** | |
| **Bot-active meetings/month** | 2,800 × 57% | **~1,596 meetings/month** |
| **Round to baseline** | | **~1,600 meetings/month** |

### 1.6 Total Bot-Hours Per Month

| Meeting Type | Count/Month | Avg Duration | Bot-Hours/Month |
|-------------|-------------|--------------|----------------|
| Daily standups (3-person teams, with agenda) | 726 | 20 min = 0.33 hr | 239.6 |
| Sprint planning (per team) | 66 | 90 min = 1.50 hr | 99.0 |
| Sprint retrospective | 66 | 60 min = 1.00 hr | 66.0 |
| Backlog grooming | 66 | 60 min = 1.00 hr | 66.0 |
| Sprint demo | 66 | 45 min = 0.75 hr | 49.5 |
| Feature kickoff meetings | 99 | 60 min = 1.00 hr | 99.0 |
| Tech design discussions | 198 | 75 min = 1.25 hr | 247.5 |
| KT sessions | 264 | 65 min = 1.08 hr | 285.1 |
| Cross-team dependency calls | 176 | 30 min = 0.50 hr | 88.0 |
| Pre-release / QA discussions | 99 | 45 min = 0.75 hr | 74.3 |
| Product reviews / demos | 60 | 55 min = 0.92 hr | 55.0 |
| Customer / sales calls | 80 | 45 min = 0.75 hr | 60.0 |
| Leadership / all-hands | 30 | 55 min = 0.92 hr | 27.5 |
| HR hiring debriefs | 50 | 30 min = 0.50 hr | 25.0 |
| Cross-functional syncs (PM-Eng-Design) | 100 | 40 min = 0.67 hr | 66.7 |
| Engineering Manager 1:1s (opted-in) | 60 | 30 min = 0.50 hr | 30.0 |
| **Engineerg-only subtotal** | **1,246** | | **1,522.2** |
| **Non-engineering subtotal** | **354** | | **234.2** |
| **Grand Total** | **1,600** | **50 min avg** | **1,537.2 hrs** |

---

## Section 2: Vexa API Cost (Meeting Bot)

Vexa charges per bot-minute the bot is inside a meeting recording transcript.

### 2.1 Vexa Pricing

| Tier | Rate | Applies When |
|------|------|-------------|
| Pay-as-you-go | $0.15 / bot-hour | <300 hrs/month |
| Growth | $0.12 / bot-hour | 300–1,000 hrs/month |
| **Business** | **$0.10 / bot-hour** | **>1,000 hrs/month** |

> At **1,537 bot-hours/month** we are firmly in the **Business tier** at $0.10/hr.

### 2.2 Monthly Vexa Cost Breakdown

| Meeting Type | Count/Month | Bot-Hours | Rate | Cost |
|-------------|-------------|-----------|------|------|
| Daily standups | 726 | 239.6 hrs | $0.10 | $23.96 |
| Sprint planning | 66 | 99.0 hrs | $0.10 | $9.90 |
| Sprint retrospective | 66 | 66.0 hrs | $0.10 | $6.60 |
| Backlog grooming | 66 | 66.0 hrs | $0.10 | $6.60 |
| Sprint demo | 66 | 49.5 hrs | $0.10 | $4.95 |
| Feature kickoff meetings | 99 | 99.0 hrs | $0.10 | $9.90 |
| Tech design discussions | 198 | 247.5 hrs | $0.10 | $24.75 |
| KT sessions | 264 | 285.1 hrs | $0.10 | $28.51 |
| Cross-team dependency calls | 176 | 88.0 hrs | $0.10 | $8.80 |
| Pre-release / QA discussions | 99 | 74.3 hrs | $0.10 | $7.43 |
| Product reviews / demos | 60 | 55.0 hrs | $0.10 | $5.50 |
| Customer / sales calls | 80 | 60.0 hrs | $0.10 | $6.00 |
| Leadership / all-hands | 30 | 27.5 hrs | $0.10 | $2.75 |
| HR hiring debriefs | 50 | 25.0 hrs | $0.10 | $2.50 |
| Cross-functional syncs | 100 | 66.7 hrs | $0.10 | $6.67 |
| EM 1:1s | 60 | 30.0 hrs | $0.10 | $3.00 |
| **Total** | **1,600** | **1,537.2 hrs** | | **$153.82/month** |

---

## Section 3: Groq API Cost (LLM — llama-3.3-70b-versatile)

The LLM is called 3 ways per meeting: agenda extraction, focus analysis
(every poll cycle), and the final report generation.

### 3.1 Tokens Per Meeting By Meeting Type

#### Call 1 — Agenda Extraction (once per meeting)
| Component | Tokens |
|-----------|--------|
| System prompt (agenda extractor) | ~500 input |
| Calendar description sent by user | ~300 input |
| LLM response (structured agenda) | ~250 output |
| **Per meeting** | **800 input / 250 output** |

#### Call 2 — Focus Analysis (each poll cycle, every 30–35 seconds)
| Component | Tokens |
|-----------|--------|
| System prompt (focus tracker) | ~700 input |
| Transcript chunk + rolling summary | ~500 input |
| LLM response (JSON analysis) | ~350 output |
| **Per cycle** | **1,200 input / 350 output** |

#### Cycles Per Meeting By Duration
| Duration | Cycles (at 35s interval) |
|----------|--------------------------|
| 15 min standups | 25 cycles |
| 30 min 1:1s | 51 cycles |
| 45 min cross-functional | 77 cycles |
| 50 min reviews | 85 cycles |
| 60 min all-hands | 102 cycles |

#### Call 3 — Professional Email Report (once per meeting)
| Component | Tokens |
|-----------|--------|
| System prompt (16-section professional) | ~2,000 input |
| Full meeting context (transcript, participants, agenda) | ~4,000 input |
| LLM response (16-section JSON report) | ~3,500 output |
| **Per meeting** | **6,000 input / 3,500 output** |

### 3.2 Total Tokens Per Meeting Type

| Meeting Type | Duration | Focus Cycles | Input Tokens | Output Tokens |
|-------------|----------|-------------|-------------|--------------|
| Daily standups | 18 min | 30 | 800 + (30×1,200) + 6,000 = **42,800** | 250 + (30×350) + 3,500 = **14,250** |
| Sprint ceremonies | 75 min | 128 | 800 + (128×1,200) + 6,000 = **160,400** | 250 + (128×350) + 3,500 = **48,550** |
| Engineering design reviews | 50 min | 85 | 800 + (85×1,200) + 6,000 = **108,800** | 250 + (85×350) + 3,500 = **33,500** |
| 1:1s | 30 min | 51 | 800 + (51×1,200) + 6,000 = **67,800** | 250 + (51×350) + 3,500 = **21,600** |
| Product reviews / demos | 55 min | 94 | 800 + (94×1,200) + 6,000 = **119,600** | 250 + (94×350) + 3,500 = **36,650** |
| Customer / sales calls | 45 min | 77 | 800 + (77×1,200) + 6,000 = **99,200** | 250 + (77×350) + 3,500 = **30,700** |
| Cross-functional syncs | 40 min | 68 | 800 + (68×1,200) + 6,000 = **88,400** | 250 + (68×350) + 3,500 = **27,550** |
| Leadership / all-hands | 55 min | 94 | 800 + (94×1,200) + 6,000 = **119,600** | 250 + (94×350) + 3,500 = **36,650** |
| HR hiring debriefs | 30 min | 51 | 800 + (51×1,200) + 6,000 = **67,800** | 250 + (51×350) + 3,500 = **21,600** |

### 3.3 Monthly Token Totals

| Meeting Type | Count/Month | Input Tokens Each | Output Tokens Each | Total Input | Total Output |
|-------------|-------------|-------------------|--------------------|-------------|-------------|
| Daily standups (20 min) | 726 | 42,800 | 14,250 | 31,072,800 | 10,345,500 |
| Sprint planning (90 min) | 66 | 160,400 | 48,550 | 10,586,400 | 3,204,300 |
| Sprint retrospective (60 min) | 66 | 108,800 | 33,500 | 7,180,800 | 2,211,000 |
| Backlog grooming (60 min) | 66 | 108,800 | 33,500 | 7,180,800 | 2,211,000 |
| Sprint demo (45 min) | 66 | 88,400 | 27,550 | 5,834,400 | 1,818,300 |
| Feature kickoff (60 min) | 99 | 108,800 | 33,500 | 10,771,200 | 3,316,500 |
| Tech design discussions (75 min) | 198 | 139,400 | 42,800 | 27,601,200 | 8,474,400 |
| KT sessions (65 min) | 264 | 120,200 | 37,050 | 31,732,800 | 9,781,200 |
| Cross-team dependency calls (30 min) | 176 | 67,800 | 21,600 | 11,932,800 | 3,801,600 |
| Pre-release / QA discussions (45 min) | 99 | 88,400 | 27,550 | 8,751,600 | 2,727,450 |
| Product reviews / demos (55 min) | 60 | 108,800 | 33,500 | 6,528,000 | 2,010,000 |
| Customer / sales calls (45 min) | 80 | 88,400 | 27,550 | 7,072,000 | 2,204,000 |
| Leadership / all-hands (55 min) | 30 | 108,800 | 33,500 | 3,264,000 | 1,005,000 |
| HR hiring debriefs (30 min) | 50 | 67,800 | 21,600 | 3,390,000 | 1,080,000 |
| Cross-functional syncs (40 min) | 100 | 88,400 | 27,550 | 8,840,000 | 2,755,000 |
| EM 1:1s (30 min) | 60 | 67,800 | 21,600 | 4,068,000 | 1,296,000 |
| **TOTALS** | **1,600** | | | **185,806,800** | **58,241,250** |
| | | | | **185.8M tokens** | **58.2M tokens** |

### 3.4 Groq Cost Calculation

| Token Type | Volume | Price per 1M | Cost |
|-----------|--------|-------------|------|
| Input | 185.8M | $0.59 | $109.62 |
| Output | 58.2M | $0.79 | $45.98 |
| **Total Groq cost** | | | **$155.60/month** |

---

## Section 4: Infrastructure (AWS EC2)

### 4.1 Concurrent Meeting Estimate (IST Working Hours)

WFH Indian startups have a pronounced standup spike at 10–11 AM IST.

| Time (IST) | Meeting Activity | Concurrent Bot Meetings |
|-----------|-----------------|------------------------|
| 9:30–10:00 AM | Early standups begin | ~8 |
| 10:00–11:00 AM | **Peak standup hour** — all teams sync | ~22 |
| 11:00 AM–1:00 PM | Design reviews, planning, 1:1s | ~18 |
| 1:00–2:00 PM | Lunch — very few meetings | ~3 |
| 2:00–4:00 PM | Customer calls, cross-functional syncs | ~15 |
| 4:00–6:00 PM | Product reviews, sprint ceremonies | ~12 |
| 6:00–7:30 PM | US-overlap calls (if any) | ~5 |
| **Peak concurrent (10–11 AM)** | | **~22 meetings** |

> At 22 peak concurrent bot threads × 30MB RAM = 660MB RAM needed.
> **t3.small (2GB) is technically sufficient but t3.medium gives safety margin.**

### 4.2 EC2 Cost

| Item | Spec | On-Demand | 1-yr Reserved |
|------|------|-----------|--------------|
| EC2 instance | t3.medium (2 vCPU, 4GB) | $30.37 | $19.34 |
| EBS storage | 30GB gp3 | $2.40 | $2.40 |
| Data transfer out | ~5GB/month | $0.45 | $0.45 |
| **Infrastructure total** | | **$33.22** | **$22.19** |

---

## Section 5: Google APIs

| API | Daily Usage | Quota | Cost |
|-----|------------|-------|------|
| Google Calendar API (read events) | ~480 calls/day | 1,000,000/day | **$0** |
| Gmail API (send emails) | ~30 emails/day | 100/user/day | **$0** |
| Google OAuth (token checks) | ~50 calls/day | Unlimited | **$0** |
| **Total** | | | **$0/month** |

---

## Section 6: Supporting Services

| Service | Usage | Cost |
|---------|-------|------|
| AWS Secrets Manager | 3 secrets × $0.40 | $1.20 |
| Secrets API calls (~500/month) | $0.30 per 10K calls | $0.02 |
| CloudWatch logs (3GB/month) | $0.50/GB | $1.50 |
| CloudWatch alarms (5 alarms) | $0.10/alarm | $0.50 |
| CloudWatch metrics | Basic included | $0.00 |
| **Total** | | **$3.22/month** |

---

## Section 7: Full Monthly Cost Summary

| Component | Unit Cost | Monthly Volume | Monthly Cost | Annual Cost |
|-----------|-----------|---------------|-------------|-------------|
| **Vexa API** | $0.10/bot-hr (Business tier) | 1,537 bot-hours | $153.82 | $1,846 |
| **Groq API** | $0.59/$0.79 per 1M | 185.8M in / 58.2M out | $155.60 | $1,867 |
| **AWS EC2 t3.medium** | $30.37/month | 1 instance | $30.37 | $364 |
| **EBS + Data transfer** | — | — | $2.85 | $34 |
| **AWS Secrets Manager** | $0.40/secret | 3 secrets | $1.22 | $15 |
| **CloudWatch** | — | 3GB logs | $2.00 | $24 |
| **Google APIs** | Free | — | $0.00 | $0 |
| **TOTAL** | | | **$345.86/month** | **$4,150/year** |

### Per-Unit Economics

| Metric | Value | Calculation |
|--------|-------|-------------|
| Cost per employee/month | **$1.73** | $345.86 ÷ 200 |
| Cost per meeting | **$0.22** | $345.86 ÷ 1,600 |
| Cost per bot-hour | **$0.23** | $345.86 ÷ 1,537 hrs |
| Cost per email report sent | **$0.22** | $345.86 ÷ 1,600 |

---

## Section 8: Scenario Analysis

### Scenario A — Low Adoption (30% of 2,800 = ~840 bot-active meetings/month)
Agendas added only to key meetings — design reviews, sprint ceremonies, product reviews.
Standups, 1:1s, and ad-hoc calls excluded.

| Component | Volume | Cost |
|-----------|--------|------|
| Vexa API | 807 bot-hours × $0.12 (Growth tier) | $96.84 |
| Groq API | 97.8M in / 30.6M out tokens (840/1,600 ratio) | $81.68 |
| AWS EC2 t3.small (lower concurrency) | — | $17.85 |
| Other | — | $3.22 |
| **Total** | | **$199.59/month** |
| **Per user** | | **$1.00/user** |

### Scenario B — Baseline (57% filtering, ~1,600 bot-active meetings/month) ← **Current**

| Component | Volume | Cost |
|-----------|--------|------|
| All as per Section 7 above | | |
| **Total** | | **$345.86/month** |
| **Per user** | | **$1.73/user** |

### Scenario C — Full Adoption (80% of 2,800 = ~2,240 bot-active meetings/month)
All recurring meetings have agendas; team fully bought in. Standups + 1:1s included.

| Component | Volume | Cost |
|-----------|--------|------|
| Vexa API | 2,150 bot-hours × $0.10 (Business tier) | $215.00 |
| Groq API | 260.1M in / 81.5M out tokens (2,240/1,600 ratio) | $218.04 |
| AWS EC2 t3.medium (upgrade headroom) | — | $30.37 |
| Other | — | $3.22 |
| **Total** | | **$466.63/month** |
| **Per user** | | **$2.33/user** |

> Even at full adoption (2,240 meetings) cost grows only **35%** over baseline (1,600 meetings)
> because standups at 20 min are cheap per-meeting, and Vexa stays in the $0.10/hr Business tier.

---

## Section 9: Cost vs Value (ROI)

### 9.1 Time Cost of Manual Meeting Administration Today
Using realistic Indian startup salary + benefits (INR converted at ₹84/$1)

| Role | People | Manual Min/Meeting | Meetings/Month Each | Total Manual Hrs/Month | Avg Cost/Hr (USD) |
|------|--------|-------------------|--------------------|-----------------------|------------------|
| Founders / C-suite | 5 | 35 min | 47 | 138 hrs | $35/hr |
| VPs / Directors | 8 | 25 min | 38 | 127 hrs | $22/hr |
| Eng Managers / TLs | 15 | 20 min | 31 | 155 hrs | $15/hr |
| Senior Engineers | 40 | 15 min | 21 | 210 hrs | $12/hr |
| Engineers | 60 | 10 min | 13 | 130 hrs | $8/hr |
| Product Managers | 15 | 20 min | 33 | 165 hrs | $14/hr |
| Designers | 10 | 15 min | 19 | 47 hrs | $10/hr |
| Sales / BD | 15 | 20 min | 22 | 110 hrs | $10/hr |
| HR / Talent | 10 | 20 min | 27 | 90 hrs | $9/hr |
| Others | 22 | 10 min | 7 | 26 hrs | $7/hr |
| **Total** | **200** | | | **1,198 hrs/month** | |

> Salary basis: Senior Eng ₹25L/yr = ~$12/hr loaded; PM ₹30L/yr = ~$14/hr loaded;
> Founders valued at ₹75L/yr equivalent for time cost = ~$35/hr.

### 9.2 Hours Saved (Realistic for Indian Startup Culture)

Indian startup culture tends to have high "meeting debt" — people often
spend 20–30 minutes after every meeting catching up colleagues who missed it,
re-sharing notes on Slack, updating Jira manually.

The tool automates:
- **Meeting minutes** — 100% automated (was 10–20 min per meeting)
- **Follow-up email with action items** — 100% automated (was 10–15 min)
- **Slack MOM post** — reduces time (was 5–10 min)
- **Jira/task creation from action items** — partial automation

Realistic savings (accounting for time to read the report):

| Role | Manual Hrs/Month | % Saved | Hours Saved/Month |
|------|-----------------|---------|------------------|
| Founders / C-suite | 138 | 70% | 97 hrs |
| VPs / Directors | 127 | 65% | 83 hrs |
| Eng Managers / TLs | 155 | 65% | 101 hrs |
| Senior Engineers | 210 | 55% | 116 hrs |
| Engineers | 130 | 50% | 65 hrs |
| Product Managers | 165 | 65% | 107 hrs |
| Designers | 47 | 55% | 26 hrs |
| Sales / BD | 110 | 60% | 66 hrs |
| HR / Talent | 90 | 55% | 50 hrs |
| Others | 26 | 45% | 12 hrs |
| **Total** | **1,198 hrs** | **60% avg** | **723 hrs/month** |

### 9.3 Financial Value Created

| Role | Hours Saved | Avg Cost/Hr | Value Created |
|------|-------------|-------------|--------------|
| Founders / C-suite | 97 hrs | $35 | $3,395 |
| VPs / Directors | 83 hrs | $22 | $1,826 |
| Eng Managers / TLs | 101 hrs | $15 | $1,515 |
| Senior Engineers | 116 hrs | $12 | $1,392 |
| Engineers | 65 hrs | $8 | $520 |
| Product Managers | 107 hrs | $14 | $1,498 |
| Designers | 26 hrs | $10 | $260 |
| Sales / BD | 66 hrs | $10 | $660 |
| HR / Talent | 50 hrs | $9 | $450 |
| Others | 12 hrs | $7 | $84 |
| **Total value created** | **723 hrs** | | **$11,600/month** |

> Note: Value is deliberately conservative using Indian market salaries.
> At US-equivalent salaries (for global product companies) this is 4–5× higher.

### 9.4 ROI Summary

| Metric | Value |
|--------|-------|
| Monthly tool cost | $345.86 |
| Monthly value created (time saved) | $11,600 |
| **Monthly net value** | **$11,254** |
| **ROI** | **33.6×** |
| Payback period | **< 1 week** |
| Annual savings vs manual | **$135,048** |

---

## Section 10: Scale Economics (Future Growth)

Scaling assumption: same WFH Indian startup meeting density (8 meetings/person/month, 7.69 bot-hours/person/month).

| Org Size | Meetings/Month | Bot-Hours | Vexa Tier | Vexa Cost | Groq Cost | Infra | Total/Month | Per User |
|----------|---------------|-----------|-----------|----------|----------|-------|-------------|----------|
| 50 people | 400 | 384 hrs | Growth $0.12 | $46 | $39 | $21 | **$106** | $2.12 |
| **200 people (now)** | **1,600** | **1,537 hrs** | **Business $0.10** | **$154** | **$156** | **$36** | **$346** | **$1.73** |
| 500 people | 4,000 | 3,845 hrs | Business $0.10 | $385 | $389 | $65 | **$839** | $1.68 |
| 1,000 people | 8,000 | 7,685 hrs | Business $0.10 | $769 | $778 | $108 | **$1,655** | $1.66 |
| 2,000 people | 16,000 | 15,370 hrs | Business $0.10 | $1,537 | $1,556 | $162 | **$3,255** | $1.63 |

> Cost per user **decreases** at scale as infrastructure cost is amortised.
> All tiers above 200 people stay in the Vexa Business tier ($0.10/hr).
> Groq API has no tier discount — but llama-3.3-70b remains one of the most cost-effective frontier models.

---

## Section 11: Pilot Budget (First 30 Days)

Run a 15-person pilot for 2 weeks before full rollout.
Pilot team: 1 EM + 5 engineers + 2 PMs + 1 designer + 1 VP + 5 others.

| Item | Volume | Cost |
|------|--------|------|
| Vexa API | 40 meetings × 0.36 hr avg × $0.15 | $2.16 |
| Groq API | 40 meetings × avg 75K input / 23K output tokens | $2.97 |
| EC2 t3.small (pilot, low concurrency) | — | $15.00 |
| Google APIs | — | $0.00 |
| AWS Secrets Manager | 3 secrets | $1.22 |
| **Pilot total** | | **$21.35/month** |

> Both Vexa and Groq offer free trial credits ($10–$25 each).
> **Pilot cost could be $0 out-of-pocket for the first 2 weeks.**

---

## Section 12: Cost Summary Card (TL;DR)

| | Baseline (1,600 meetings/month) |
|---|---|
| **Monthly cost** | **$345.86** |
| **Annual cost** | **$4,150** |
| **Per employee/month** | **$1.73** |
| **Per meeting report** | **$0.22** |
| **Bot-hours/month** | **1,537 hrs** |
| **Monthly time saved** | **723 person-hours** |
| **Monthly value created** | **$11,600** |
| **ROI** | **33.6×** |
| **Annual net savings** | **$135,048** |

### Competitive Comparison

| Tool | Price Model | Cost for 200 Users |
|------|------------|-------------------|
| Otter.ai Teams | $20/user/month | **$4,000/month** |
| Fireflies.ai Business | $19/user/month | **$3,800/month** |
| Notion AI | $10/user/month | **$2,000/month** |
| **This system** | **Usage-based** | **$345.86/month** |
| **Savings vs Otter.ai** | | **91% cheaper** |

> This system is **91% cheaper** than Otter.ai and produces a **deeper 16-section analysis**
> with focus tracking, agenda enforcement, and auto-threading of recurring meetings —
> none of which any of the above tools offer out of the box.
