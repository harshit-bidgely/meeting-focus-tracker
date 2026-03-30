import json
import logging
import re
import time

from openai import OpenAI

logger = logging.getLogger(__name__)

# Common malformed-JSON patterns produced by small models
_JSON_REPAIRS = [
    (re.compile(r'": *":'), '":'),           # "key":":[  -> "key":[
    (re.compile(r",\s*}"), "}"),              # trailing comma before }
    (re.compile(r",\s*]"), "]"),              # trailing comma before ]
]


def _repair_json(text: str) -> str:
    """Best-effort repair of common LLM JSON mistakes."""
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)
    # Fix common pattern errors
    for pattern, replacement in _JSON_REPAIRS:
        text = pattern.sub(replacement, text)
    # Close truncated JSON
    if text.count('{') > text.count('}'):
        in_string = False
        for i, ch in enumerate(text):
            if ch == '"' and (i == 0 or text[i-1] != '\\'):
                in_string = not in_string
        if in_string:
            text += '"'
        text += '}' * (text.count('{') - text.count('}'))
    return text


def _extract_json_object(text: str) -> dict:
    """Extract the first top-level { ... } from text and parse it."""
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in LLM response: {text[:300]}")

    brace_depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    repaired = _repair_json(candidate)
                    try:
                        return json.loads(repaired, strict=False)
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"LLM returned invalid JSON: {exc}\nResponse was: {candidate[:300]}"
                        ) from exc

    raise ValueError(f"LLM returned incomplete JSON (truncated?): {text[:300]}")


class LLMClient:
    """Wrapper around an OpenAI-compatible API (Groq, OpenAI, etc.) that returns parsed JSON."""

    MAX_RETRIES = 3

    def __init__(self, api_key: str, model: str, api_base: str = "https://api.groq.com/openai/v1"):
        self.client = OpenAI(api_key=api_key, base_url=api_base)
        self.model = model

    def call(self, system_prompt: str, user_message: str, max_tokens: int = 1024) -> dict:
        """Send a system + user message and return parsed JSON.

        Retries up to MAX_RETRIES on rate-limit or JSON parse failures.
        """
        logger.debug("LLM call — model=%s, max_tokens=%d", self.model, max_tokens)
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
            except Exception as e:
                if "429" in str(e):
                    logger.warning("Rate limited (attempt %d), waiting 10s...", attempt + 1)
                    time.sleep(10)
                    continue
                raise

            raw_text = response.choices[0].message.content.strip()
            logger.debug("LLM raw response (attempt %d): %s", attempt + 1, raw_text[:200])

            # Strip markdown fences
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

            # Try parse: strict -> strict=False -> repair -> extract object
            for parser in [
                lambda t: json.loads(t),
                lambda t: json.loads(t, strict=False),
                lambda t: json.loads(_repair_json(t), strict=False),
                lambda t: _extract_json_object(t),
            ]:
                try:
                    return parser(cleaned)
                except (json.JSONDecodeError, ValueError):
                    continue

            last_error = f"All parse strategies failed for: {cleaned[:200]}"
            logger.warning("JSON parse failed (attempt %d/%d)", attempt + 1, self.MAX_RETRIES)
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(1)

        raise ValueError(f"LLM failed to return valid JSON after {self.MAX_RETRIES} attempts: {last_error}")
