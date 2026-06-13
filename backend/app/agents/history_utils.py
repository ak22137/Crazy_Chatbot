"""
Conversation history formatting utilities.
Shared between orchestrator and sql_agent to avoid circular imports.
"""


def format_history_context(history: list[dict]) -> str:
    """Format conversation history into a readable string for prompt injection.

    Args:
        history: List of dicts with 'role' and 'content' keys.

    Returns:
        Formatted string with "User: ..." / "Assistant: ..." lines,
        or empty string if no history.
    """
    if not history:
        return ""
    lines = []
    for msg in history:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        # Truncate long assistant responses to keep the prompt focused
        content = msg["content"]
        if msg["role"] == "assistant" and len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"{role_label}: {content}")
    return "\n".join(lines)
