"""
Query Orchestrator.
Receives user question, classifies intent, routes to the right agent,
and composes the final response.
"""

import json
import logging
import time

import duckdb

from app.llm.mistral_client import chat, chat_stream, parse_json_response
from app.llm.prompts import (
    INTENT_CLASSIFICATION,
    RESPONSE_FORMAT,
    METADATA_RESPONSE,
)
from app.agents.sql_agent.agent import run_sql_agent, SQLResult
from app.agents.history_utils import format_history_context
from app.ingestion.metadata_builder import get_all_metadata

logger = logging.getLogger(__name__)


def _build_brief_schema(metadata: dict) -> str:
    """Build a brief schema summary for intent classification."""
    lines = []
    for tbl, info in metadata.items():
        cols = list(info["columns"].keys())
        lines.append(f"- {tbl} ({info['row_count']} rows): {', '.join(cols)}")
    return "\n".join(lines) or "No tables available."



def classify_intent(
    question: str,
    read_conn: duckdb.DuckDBPyConnection,
    history: list[dict] | None = None,
) -> dict:
    """
    Classify the user's question intent.

    Returns:
        {"intent": str, "confidence": float, "reason": str}
    """
    metadata = get_all_metadata(read_conn)
    schema_context = _build_brief_schema(metadata)

    history_context = format_history_context(history or [])

    prompt = INTENT_CLASSIFICATION.format(
        schema_context=schema_context,
        question=question,
        conversation_history=history_context,
    )

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=256,
        json_mode=True,
    )

    result = parse_json_response(response)
    if not result or "intent" not in result:
        return {"intent": "SQL_ANALYTICS", "confidence": 0.5, "reason": "Defaulting to SQL"}
    return result


def handle_question(
    question: str,
    read_conn: duckdb.DuckDBPyConnection,
    write_conn: duckdb.DuckDBPyConnection,
    history: list[dict] | None = None,
) -> dict:
    """
    Full synchronous question handling pipeline.

    Returns dict with:
        - intent: classified intent
        - answer: natural language response
        - sql_result: SQL result data (if SQL_ANALYTICS)
        - metadata: metadata info (if METADATA)
    """
    start = time.time()
    history = history or []

    # 1. Classify intent
    intent_result = classify_intent(question, read_conn, history=history)
    intent = intent_result.get("intent", "SQL_ANALYTICS")
    logger.info(f"Intent: {intent} (confidence: {intent_result.get('confidence', 0)})")

    response_data = {
        "intent": intent,
        "answer": "",
        "sql_result": None,
    }

    history_context = format_history_context(history)

    # 2. Route to agent
    if intent == "GREETING":
        response_data["answer"] = _handle_greeting(question)

    elif intent == "METADATA":
        metadata = get_all_metadata(read_conn)
        prompt = METADATA_RESPONSE.format(
            metadata=json.dumps(metadata, indent=2, default=str),
            question=question,
            conversation_history=history_context,
        )
        response_data["answer"] = chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )

    elif intent == "SQL_ANALYTICS":
        sql_result = run_sql_agent(question, read_conn, write_conn, history=history)
        response_data["sql_result"] = sql_result.to_dict()

        if sql_result.success:
            # Format the response
            prompt = RESPONSE_FORMAT.format(
                question=question,
                sql=sql_result.sql,
                results=sql_result.results_as_text(),
                row_count=sql_result.row_count,
                conversation_history=history_context,
            )
            response_data["answer"] = chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1024,
            )
        else:
            response_data["answer"] = (
                f"I wasn't able to answer that question. "
                f"Error: {sql_result.error}\n\n"
                f"Could you try rephrasing your question?"
            )

    else:
        # Default: try SQL
        sql_result = run_sql_agent(question, read_conn, write_conn, history=history)
        response_data["sql_result"] = sql_result.to_dict()
        if sql_result.success:
            prompt = RESPONSE_FORMAT.format(
                question=question,
                sql=sql_result.sql,
                results=sql_result.results_as_text(),
                row_count=sql_result.row_count,
                conversation_history=history_context,
            )
            response_data["answer"] = chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1024,
            )
        else:
            response_data["answer"] = f"I couldn't process that question. Error: {sql_result.error}"

    elapsed = (time.time() - start) * 1000
    response_data["processing_time_ms"] = round(elapsed, 2)
    logger.info(f"Question handled in {elapsed:.0f}ms")

    return response_data


def _handle_greeting(question: str) -> str:
    """Handle greeting/help questions."""
    q = question.lower().strip()
    if any(w in q for w in ["hello", "hi", "hey"]):
        return (
            "Hey! 👋 I'm your Excel analytics assistant. "
            "Upload some Excel or CSV files and then ask me questions about your data. "
            "I can count, filter, aggregate, compare, and find trends. Try asking something like:\n\n"
            "- *How many rows are in the table?*\n"
            "- *What's the average salary by department?*\n"
            "- *Show me the top 10 candidates*\n"
            "- *What tables do I have?*"
        )
    return (
        "I can help you analyze your Excel and CSV data! "
        "Upload a file using the upload button, then ask me questions about your data. "
        "I use SQL to give you accurate, deterministic answers — no guessing."
    )

