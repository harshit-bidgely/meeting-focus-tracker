import json
import logging
import re

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper around an OpenAI-compatible API (Groq, OpenAI, etc.) that returns parsed JSON."""

    def __init__(self, api_key: str, model: str, api_base: str = "https://api.groq.com/openai/v1"):
        self.client = OpenAI(api_key=api_key, base_url=api_base)
        self.model = model

    @staticmethod
    def _repair_json(text: str) -> str:
        """Best-effort repair of truncated or malformed JSON from the LLM."""
        # Remove control characters inside string values (tabs, literal newlines)
        # that break strict JSON parsing — replace with spaces
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)

        # If JSON appears truncated (no closing brace), try to close it
        if text.count('{') > text.count('}'):
            # Truncated inside a string value — close the string and objects
            # Find if we're inside a string (odd number of unescaped quotes)
            in_string = False
            for i, ch in enumerate(text):
                if ch == '"' and (i == 0 or text[i-1] != '\\'):
                    in_string = not in_string
            if in_string:
                text += '"'
            # Close any open braces
            text += '}' * (text.count('{') - text.count('}'))
        return text

    def call(self, system_prompt: str, user_message: str, max_tokens: int = 1024) -> dict:
        """Send a system + user message and return parsed JSON. Retries once on rate limit."""
        logger.debug("LLM call — model=%s, max_tokens=%d", self.model, max_tokens)
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
                break
            except Exception as e:
                if "429" in str(e) and attempt == 0:
                    import time
                    logger.warning("Rate limited, waiting 10s before retry...")
                    time.sleep(10)
                else:
                    raise
        raw_text = response.choices[0].message.content.strip()
        logger.debug("LLM raw response: %s", raw_text[:200])

        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Try strict parse first, then lenient with repair
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Attempt 2: strict=False allows control characters in strings
        try:
            return json.loads(cleaned, strict=False)
        except json.JSONDecodeError:
            pass

        # Attempt 3: repair truncated/malformed JSON then parse
        try:
            repaired = self._repair_json(cleaned)
            return json.loads(repaired, strict=False)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s", cleaned[:300])
            raise ValueError(
                f"LLM returned invalid JSON: {exc}\nResponse was: {cleaned[:300]}"
            ) from exc
