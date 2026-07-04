"""Thin wrapper around google-genai for SentinelAI agents."""
import os
import json
import re
from google import genai
from google.genai import types

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
client = None
if GOOGLE_API_KEY:
    client = genai.Client(api_key=GOOGLE_API_KEY)

DEFAULT_MODEL = "gemini-2.5-flash"


async def call_llm_json(system_prompt: str, user_prompt: str, session_id: str) -> dict:
    """Call Gemini and parse JSON response. Returns {} on parse failure."""
    if not GOOGLE_API_KEY or client is None:
        return {"_error": "GOOGLE_API_KEY not set"}

    try:
        response = await client.aio.models.generate_content(
            model=DEFAULT_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            )
        )
        return parse_json_safe(response.text)
    except Exception as e:
        return {"_error": str(e)}


def parse_json_safe(text: str) -> dict:
    """Robust JSON extraction from LLM response."""
    if not text:
        return {}
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to extract ```json ... ``` block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try to find the first {...} object
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {"_raw": text[:2000]}
