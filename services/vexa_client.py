import logging
import requests

logger = logging.getLogger(__name__)


class VexaClient:
    """Wrapper for the Vexa REST API (transcripts + interactive bots)."""

    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        }

    def start_bot(
        self, platform: str, meeting_id: str, bot_name: str = "FocusBot"
    ) -> dict:
        """POST /bots — join a meeting with an interactive bot."""
        url = f"{self.api_base}/bots"
        payload = {
            "platform": platform,
            "native_meeting_id": meeting_id,
            "bot_name": bot_name,
        }
        logger.info("Starting bot for %s/%s", platform, meeting_id)
        resp = requests.post(url, json=payload, headers=self.headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Bot started: %s", data)
        return data

    def get_transcript(self, platform: str, meeting_id: str) -> dict:
        """GET /transcripts/{platform}/{meeting_id} — fetch transcript segments."""
        url = f"{self.api_base}/transcripts/{platform}/{meeting_id}"
        logger.debug("Fetching transcript from %s", url)
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        segment_count = len(data.get("segments", []))
        logger.debug("Received %d segments", segment_count)
        return data

    def send_chat(self, platform: str, meeting_id: str, text: str) -> dict:
        """POST /bots/{platform}/{meeting_id}/chat — send a message into the live meeting chat."""
        url = f"{self.api_base}/bots/{platform}/{meeting_id}/chat"
        payload = {"text": text}
        logger.info("Sending chat to %s/%s: %s", platform, meeting_id, text[:80])
        resp = requests.post(url, json=payload, headers=self.headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Chat sent: %s", data)
        return data

    def stop_bot(self, platform: str, meeting_id: str) -> None:
        """DELETE /bots/{platform}/{meeting_id} — remove bot from meeting."""
        url = f"{self.api_base}/bots/{platform}/{meeting_id}"
        logger.info("Stopping bot for %s/%s", platform, meeting_id)
        resp = requests.delete(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        logger.info("Bot stopped")
