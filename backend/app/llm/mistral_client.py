"""
LLM client wrapper using Siemens chat completions API.
"""

import json
import logging
import re

import requests

from app.config import settings

logger = logging.getLogger(__name__)


def chat(
    messages: list[dict],
    temperature: float = 0.0,
    max_tokens: int = 2048,
    json_mode: bool = False,
) -> str:
    """Send a chat completion request to the configured LLM API."""
    payload = {
        "model": settings.llm_model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        settings.llm_api_url,
        headers=headers,
        json=payload,
        timeout=settings.llm_timeout_sec,
    )
    response.raise_for_status()

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Unexpected LLM response shape: {data}")
        raise ValueError("LLM response missing choices[0].message.content") from e

    if isinstance(content, list):
        # Some providers return content parts instead of one string.
        return "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


async def chat_stream(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 2048,
):
    """Lightweight streaming helper by chunking a non-streamed response."""
    full_text = chat(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    for token in full_text.split(" "):
        yield token + " "


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from an LLM response.

    Handles plain JSON, fenced JSON blocks, and responses with extra prose.
    """
    text = text.strip()
    if not text:
        return {}

    # Remove markdown fences like ```json ... ``` if present.
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # First attempt: direct JSON parse.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: parse the first JSON object substring.
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}")
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Last fallback: scan for fenced JSON blocks anywhere in text.
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE):
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    logger.error(f"Failed to parse JSON from LLM response. Text: {text[:500]}")
    return {}
