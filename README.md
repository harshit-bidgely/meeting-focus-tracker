# Meeting Focus Tracker

Real-time meeting focus tracker that monitors live Google Meet conversations via the Vexa transcription API, compares them against a predefined agenda, detects when discussion drifts off-topic, and sends alerts directly into the meeting chat.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys and meeting ID
```

## Configuration (.env)

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `VEXA_API_KEY` | Your Vexa API key |
| `MEETING_ID` | Google Meet meeting ID (e.g. `yew-sbdv-tjt`) |
| `MEETING_PLATFORM` | Platform identifier (default: `google_meet`) |
| `POLL_INTERVAL_SECONDS` | Seconds between transcript polls (default: 60) |
| `DEVIATION_THRESHOLD` | Consecutive deviations before alert (default: 2) |
| `ALERT_COOLDOWN_SECONDS` | Minimum seconds between alerts (default: 180) |
| `CALENDAR_DESCRIPTION` | Calendar event description with agenda |
| `LLM_MODEL` | Claude model to use (default: `claude-sonnet-4-20250514`) |

## Usage

```bash
python main.py
```

If `CALENDAR_DESCRIPTION` is not set, you'll be prompted to paste the calendar event description. The tracker then enters a 60-second polling loop:

1. Fetches new transcript segments from Vexa
2. Cleans and de-noises the raw transcript
3. Sends the chunk to Claude for focus analysis
4. Updates deviation counter and rolling summary
5. Sends an alert into the meeting chat if off-topic for too long

## Tests

```bash
python -m pytest tests/ -v
```

## Architecture

- **Prompt 1 (Agenda Extractor)**: Extracts structured agenda from calendar description (runs once)
- **Prompt 2 (Focus Tracker)**: Classifies each transcript chunk as `on_track`, `tangential`, `off_topic`, or `insufficient_data`
- **Rolling Summary**: Two-part format (narrative + agenda tracker) keeps token budget flat regardless of meeting length
- **Alert System**: Vexa Interactive Bots API sends messages directly into the Google Meet chat
