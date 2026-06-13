"""
Conversation history formatting utilities.
Shared between orchestrator and sql_agent to avoid circular imports.
"""

import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Character cap for history content injected into prompts ──────────────────
# Keeps prompts lean so the LLM focuses on the new question.
HISTORY_CHAR_LIMIT = 300


@dataclass
class LastExchangeCache:
    """Stores the last exchange so follow-ups can skip redundant LLM calls."""

    question: str = ""
    intent: str = ""
    sql: str = ""
    result_summary: str = ""       # Truncated text summary of query results
    selected_tables: list[str] = field(default_factory=list)
    timestamp: float = 0.0

    # Cache is valid for 5 minutes
    TTL_SECONDS: float = 300.0

    def is_valid(self) -> bool:
        """Check if cache is still fresh."""
        return bool(self.question) and (time.time() - self.timestamp) < self.TTL_SECONDS

    def update(
        self,
        question: str,
        intent: str,
        sql: str = "",
        result_summary: str = "",
        selected_tables: list[str] | None = None,
    ) -> None:
        self.question = question
        self.intent = intent
        self.sql = sql
        self.result_summary = result_summary[:500] if result_summary else ""
        self.selected_tables = selected_tables or []
        self.timestamp = time.time()
        logger.debug(f"Cache updated: intent={intent}, sql_len={len(sql)}")

    def clear(self) -> None:
        self.question = ""
        self.intent = ""
        self.sql = ""
        self.result_summary = ""
        self.selected_tables = []
        self.timestamp = 0.0


# Module-level singleton — survives across requests in the same process
_exchange_cache = LastExchangeCache()


def get_exchange_cache() -> LastExchangeCache:
    return _exchange_cache


def _truncate(text: str, limit: int) -> str:
    """Truncate text to limit, appending '...' if shortened."""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def format_history_context(history: list[dict], char_limit: int = HISTORY_CHAR_LIMIT) -> str:
    """Format conversation history into a readable string for prompt injection.

    Args:
        history: List of dicts with 'role' and 'content' keys.
        char_limit: Max characters per message content (default HISTORY_CHAR_LIMIT).

    Returns:
        Formatted string with "User: ..." / "Assistant: ..." lines,
        or empty string if no history.
    """
    if not history:
        return ""
    lines = []
    for msg in history:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        content = _truncate(msg["content"], char_limit)
        lines.append(f"{role_label}: {content}")
    return "\n".join(lines)
