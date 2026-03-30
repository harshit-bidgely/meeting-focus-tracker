# Meeting Focus Tracker

A tool that listens to your Google Meet in real-time, checks if the conversation is following the agenda, and alerts you (with a popup on your screen) when the discussion goes off-topic. It also remembers past meetings and can tell you when a meeting is just repeating the same things without progress.

---

## What Does This Tool Do?

Imagine you have a meeting about "Q3 Sales Strategy." You set the agenda beforehand. During the meeting, someone starts talking about their weekend plans. This tool will:

1. **Detect** that the conversation drifted off-topic
2. **Show a popup notification** on your Mac screen saying "Off Topic! Get back to Q3 Sales Strategy"
3. **Remember** what was discussed, so if the same meeting happens next week and the same points are repeated without new decisions, it flags it as **repetitive**

---

## Before You Start (What You Need)

You need three things:

| What | Where to get it | Cost |
|------|-----------------|------|
| **Groq API key** | Go to [console.groq.com](https://console.groq.com), sign in with Google, click "API Keys" on the left, click "Create API Key" | Free |
| **Vexa API key** | Your team should have this. It's the key that lets the bot join Google Meet and listen to the conversation | Ask your team |
| **Python 3** | Open Terminal and type `python3 --version`. If it shows a version number, you're good | Already on Mac |

---

## Step-by-Step Setup

### Step 1: Download the project

Open the **Terminal** app on your Mac (search for "Terminal" in Spotlight) and run:

```
git clone https://github.com/harshit-bidgely/meeting-focus-tracker.git
cd meeting-focus-tracker
```

### Step 2: Install the required software

Still in Terminal, run:

```
pip3 install -r requirements.txt
```

This installs the libraries the tool needs. It takes about 30 seconds.

### Step 3: Set up your configuration file

Run:

```
cp .env.example .env
```

This creates your personal config file. Now open it in any text editor:

```
open -e .env
```

You'll see something like this:

```
LLM_API_KEY=your_groq_api_key_here
LLM_API_BASE=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
VEXA_API_KEY=your_vexa_api_key_here
VEXA_API_BASE=https://api.cloud.vexa.ai
MEETING_PLATFORM=google_meet
MEETING_ID=abc-defg-hij
POLL_INTERVAL_SECONDS=60
DEVIATION_THRESHOLD=2
ALERT_COOLDOWN_SECONDS=180
CALENDAR_DESCRIPTION=
```

**Fill in these fields:**

| Field | What to put | Example |
|-------|-------------|---------|
| `LLM_API_KEY` | Your Groq API key (from Step "Before You Start") | `gsk_abc123...` |
| `VEXA_API_KEY` | Your Vexa API key | `EjC8zCSg5B...` |
| `MEETING_ID` | The last part of your Google Meet link (after `meet.google.com/`) | `abc-defg-hij` |
| `CALENDAR_DESCRIPTION` | Your meeting agenda. Just type what the meeting is about | `Team standup: 1. Sprint progress 2. Blockers 3. Next steps` |

**Leave everything else as-is.** Save and close the file.

### Step 4: Start a Google Meet and get the meeting code

1. Open Google Meet and start or join a meeting
2. Look at the URL in your browser. It looks like: `https://meet.google.com/abc-defg-hij`
3. The part after `meet.google.com/` is your meeting code: `abc-defg-hij`
4. Put this in your `.env` file as `MEETING_ID`

### Step 5: Run the tracker

In Terminal, run:

```
python3 main.py
```

You'll see:

```
============================================================
  MEETING FOCUS TRACKER
============================================================
  Platform : google_meet
  Meeting  : abc-defg-hij
  Poll     : every 60s
  AGENDA:
    1. Sprint progress
    2. Blockers
    3. Next steps
============================================================
```

**Important:** A bot called "FocusBot" will try to join your Google Meet. You need to **admit it** (click "Accept" when you see it asking to join).

### Step 6: Talk in your meeting

The tool checks the conversation every 60 seconds. You'll see output like:

```
[Cycle 1] ✅ ON_TRACK           | Discussing sprint progress
[Cycle 2] ✅ ON_TRACK           | Reviewing blockers
[Cycle 3] 🔴 OFF_TOPIC          | Weekend plans discussion
```

If the conversation stays off-topic for 2 checks in a row, you'll get a **popup notification** on your screen with a sound.

### Step 7: Stop the tracker

Press `Ctrl + C` in Terminal. The tool will save a summary of the meeting to memory before exiting.

---

## What Each Setting Does

| Setting | What it controls | Default | When to change |
|---------|-----------------|---------|----------------|
| `POLL_INTERVAL_SECONDS` | How often (in seconds) it checks the conversation | 60 | Lower it (e.g. 30) for faster detection, raise it (e.g. 120) to save API calls |
| `DEVIATION_THRESHOLD` | How many off-topic checks before it alerts you | 2 | Raise to 3 if you get too many alerts, lower to 1 for strict mode |
| `ALERT_COOLDOWN_SECONDS` | Minimum seconds between popup alerts | 180 (3 min) | Lower it (e.g. 45) if you want more frequent alerts |
| `LLM_MODEL` | Which AI model analyzes the conversation | llama-3.3-70b-versatile | Try `llama-3.1-8b-instant` if you hit rate limits |
| `MEMORY_STORAGE_PATH` | Where past meeting data is stored on your computer | `~/.meeting_focus_tracker/meeting_history.json` | Change if you want it somewhere else |
| `MEMORY_SIMILARITY_THRESHOLD` | How similar two agenda topics need to be to count as "related" | 0.55 | Lower (e.g. 0.4) to catch more matches, raise (e.g. 0.7) for stricter matching |

---

## Where Is Everything Stored?

### Meeting Memory (Past Meetings)

Location: **`~/.meeting_focus_tracker/meeting_history.json`**

This is a file on your computer (in your home folder, inside a hidden folder called `.meeting_focus_tracker`). It stores:

- The date of each past meeting
- What the agenda was
- A summary of what was discussed
- Key decisions that were made
- Open items that still need action

To see it, run:

```
cat ~/.meeting_focus_tracker/meeting_history.json
```

To **delete all memory** and start fresh:

```
rm ~/.meeting_focus_tracker/meeting_history.json
```

### Your Config

Location: **`meeting-focus-tracker/.env`**

This file has your API keys and settings. It is **never uploaded to GitHub** (it's in the `.gitignore` file).

### Nothing goes to the cloud

All meeting data stays on your computer. The only external calls are:
- **Vexa** (to get the live transcript from Google Meet)
- **Groq** (to analyze the transcript with AI)

No meeting content is stored on any server. The AI processes it and forgets it immediately.

---

## How the Cross-Meeting Memory Works

### Automatic saving

Every time you stop the tracker (`Ctrl + C`), it automatically saves:
- What agenda items were discussed
- The summary of the conversation
- Any decisions made
- Any open/unresolved items

### Automatic recall

Next time you run the tracker with a similar agenda, it:
1. Looks at your new agenda items
2. Fuzzy-matches them against past meetings (so "Q3 Sales Strategy" matches "Q3 Sales Planning")
3. If it finds related past meetings, it tells the AI about them
4. The AI then checks: **is this meeting making progress, or just repeating?**

### What you'll see

If a meeting is repeating past discussions:
```
[Cycle 3] 🔴 OFF_TOPIC          | Revenue discussion
  REPEAT     : Same revenue issues discussed in March 23 meeting without new decisions
```

If a meeting is making progress:
```
[Cycle 3] ✅ ON_TRACK           | Interview pipeline review
  PROGRESS   : Building on previous decision to hire 3 backend engineers
```

---

## Troubleshooting

### "FocusBot" doesn't appear in my Google Meet
- Make sure the `MEETING_ID` in your `.env` matches your actual meeting code
- Make sure the Vexa API key is correct
- The bot takes about 30 seconds to join after you start the tracker

### I don't see any popup notifications
- Go to **System Settings > Notifications > Script Editor** on your Mac
- Make sure notifications are allowed
- Make sure "Do Not Disturb" is off

### "Rate limit" error
- The free Groq tier has limits. Wait 2-3 minutes and restart
- Or switch to `llama-3.1-8b-instant` model in your `.env` (uses fewer tokens)

### "Insufficient new transcript" every cycle
- Make sure people are actually talking in the meeting
- Make sure the FocusBot was admitted into the meeting
- The bot needs to hear audio to transcribe

### I want to start with fresh memory
```
rm ~/.meeting_focus_tracker/meeting_history.json
```

---

## Google Workspace (G Suite) Integration

The tracker can optionally connect to your Google account to:

- **Google Calendar** — Auto-fetch the meeting agenda and Google Meet ID from your calendar (no more manual `CALENDAR_DESCRIPTION` / `MEETING_ID`)
- **Gmail** — Email a meeting summary report to all attendees when the meeting ends
- **Google Drive** — Save meeting notes as a Google Doc in a "Meeting Focus Tracker Notes" folder

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Go to **APIs & Services > Library** and enable these APIs:
   - Google Calendar API
   - Gmail API
   - Google Drive API
   - Google Docs API

### Step 2: Create OAuth2 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure the **OAuth consent screen** first:
   - Choose "External" (or "Internal" if using Google Workspace)
   - Add your email as a test user
4. For Application type, choose **Desktop app**
5. Download the JSON file and save it as `credentials.json` in the project root

### Step 3: Enable in .env

Add these lines to your `.env` file:

```
# Google Workspace — set to true to enable each feature
ENABLE_GOOGLE_CALENDAR=true
ENABLE_GMAIL_SUMMARY=true
ENABLE_GOOGLE_DRIVE=true

# Optional: path to your credentials file (default: credentials.json)
GOOGLE_CREDENTIALS_FILE=credentials.json

# Optional: which calendar to read (default: primary)
GOOGLE_CALENDAR_ID=primary
```

### Step 4: First Run — Authorize

When you run `python3 main.py` with Google features enabled, a browser window will open asking you to sign in and authorize the app. This only happens once — after that, the token is saved in `token.json`.

### Google Workspace Settings

| Setting | What it controls | Default |
|---------|-----------------|---------|
| `ENABLE_GOOGLE_CALENDAR` | Auto-fetch agenda & Meet ID from Calendar | `false` |
| `ENABLE_GMAIL_SUMMARY` | Email summary to attendees on meeting end | `false` |
| `ENABLE_GOOGLE_DRIVE` | Save meeting notes as Google Doc | `false` |
| `GOOGLE_CREDENTIALS_FILE` | Path to OAuth client secrets JSON | `credentials.json` |
| `GOOGLE_TOKEN_FILE` | Path to cached OAuth token | `token.json` |
| `GOOGLE_CALENDAR_ID` | Which calendar to read events from | `primary` |

### Important Notes

- `credentials.json` and `token.json` are in `.gitignore` — they are never uploaded to GitHub
- The first time you enable Google features, you must be at your computer to authorize in the browser
- If you only want Calendar auto-fetch (no email/drive), just set `ENABLE_GOOGLE_CALENDAR=true`
- Gmail sends emails **from your account** to the attendees listed on the calendar event

---

## Auto Mode — Hands-Free Bot Invites

Auto mode watches your Google Calendar and **automatically prompts you to invite FocusBot** whenever a meeting with a Google Meet link is about to start.

### How It Works

1. You run `python3 main.py --auto`
2. The watcher polls your Google Calendar every 30 seconds
3. When a meeting is starting (within 2 minutes), a **macOS popup** appears:
   ```
   Meeting: Sprint Sync
   starts in 1 min

   Join & invite FocusBot to track focus?

   [Skip]  [Invite FocusBot]
   ```
4. Click **"Invite FocusBot"** → the bot joins the meeting, tracking starts
5. Click **"Skip"** → that meeting is skipped, watcher continues watching
6. When the meeting ends, summary is saved and the watcher goes back to watching for the next meeting

### Start Auto Mode

```
python3 main.py --auto
```

### Auto Mode Settings

| Setting | What it controls | Default |
|---------|-----------------|---------|
| `AUTO_JOIN_LEAD_MINUTES` | How many minutes before meeting start to show the prompt | `2` |
| `CALENDAR_POLL_INTERVAL` | How often (seconds) to check the calendar | `30` |

### Requirements

- Auto mode requires Google OAuth2 credentials (`credentials.json`)
- Works without `ENABLE_GOOGLE_CALENDAR=true` — auto mode enables Calendar reading automatically
- Still requires `LLM_API_KEY` and `VEXA_API_KEY`

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start the tracker (manual) | `python3 main.py` |
| Start the tracker (auto) | `python3 main.py --auto` |
| Stop the tracker | `Ctrl + C` |
| Run tests | `python3 -m pytest tests/ -v` |
| Query meeting history | `python3 query.py all` |
| View past meeting memory | `cat ~/.meeting_focus_tracker/meeting_history.json` |
| Delete all memory | `rm ~/.meeting_focus_tracker/meeting_history.json` |
| Edit settings | `open -e .env` |
