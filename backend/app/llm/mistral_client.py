"""
Mistral AI client wrapper.
Provides chat completion and streaming using mistral-small-latest.
"""

import json
import logging
from mistralai import Mistral
from app.config import settings

logger = logging.getLogger(__name__)

_client: Mistral | None = None


def _get_client() -> Mistral:
    global _client
    if _client is None:
        _client = Mistral(api_key=settings.mistral_api_key)
    return _client


def chat(
    messages: list[dict],
    temperature: float = 0.0,
    max_tokens: int = 2048,
    json_mode: bool = False,
) -> str:
    """
    Send a chat completion request to Mistral.

    Args:
        messages: List of {"role": "...", "content": "..."} dicts.
        temperature: Sampling temperature (0 = deterministic).
        max_tokens: Maximum response tokens.
        json_mode: If True, request JSON output.

    Returns:
        The assistant's response text.
    """
    client = _get_client()
    kwargs = {
        "model": settings.mistral_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.complete(**kwargs)
    return response.choices[0].message.content


async def chat_stream(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 2048,
):
    """
    Stream a chat completion response from Mistral, yielding tokens.

    Yields:
        str: Individual token strings.
    """
    client = _get_client()
    response = client.chat.stream(
        model=settings.mistral_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    for event in response:
        if event.data.choices and event.data.choices[0].delta.content:
            yield event.data.choices[0].delta.content


def parse_json_response(text: str) -> dict:
    """
    Extract and parse JSON from an LLM response.
    Handles responses wrapped in ```json ... ``` blocks.
    """
    text = text.strip()
    # Remove markdown code fences
    if text.startswith("```"):
        lines = text.split('\n')
        lines = lines[1:]  # Remove opening fence
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {e}\nText: {text[:500]}")
        return {}
