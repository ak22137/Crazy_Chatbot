"""
Chat API endpoint.
Handles user questions via SSE streaming or synchronous response.
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.database.connection import get_write_connection, read_connection
from app.agents.orchestrator.orchestrator import handle_question

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


class HistoryMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[HistoryMessage] = []


class ChatResponse(BaseModel):
    intent: str
    answer: str
    sql_result: dict | None = None
    processing_time_ms: float = 0


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Send a question and get a response.

    The system will:
    1. Classify the question intent (SQL_ANALYTICS, METADATA, GREETING)
    2. Route to the appropriate agent
    3. Return a natural language answer with optional SQL results
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    write_conn = get_write_connection()
    history = [{"role": h.role, "content": h.content} for h in request.history]

    with read_connection() as read_conn:
        result = handle_question(request.question, read_conn, write_conn, history=history)

    return ChatResponse(**result)


@router.post("/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Send a question and receive a streaming SSE response.

    Events:
    - intent: The classified intent
    - sql: The generated SQL (if applicable)
    - token: Individual response tokens
    - result: The full SQL result data
    - done: Stream complete
    - error: Error occurred
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    history = [{"role": h.role, "content": h.content} for h in request.history]

    async def event_stream():
        try:
            write_conn = get_write_connection()

            with read_connection() as read_conn:
                result = handle_question(request.question, read_conn, write_conn, history=history)

            # Send intent
            yield f"data: {json.dumps({'type': 'intent', 'data': result['intent']})}\n\n"

            # Send SQL result if present
            if result.get("sql_result"):
                yield f"data: {json.dumps({'type': 'sql', 'data': result['sql_result']})}\n\n"

            # Send answer as stream of chunks (simulate token streaming)
            answer = result.get("answer", "")
            words = answer.split(" ")
            chunk_size = 3  # Send 3 words at a time for smooth streaming
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"

            # Send completion
            yield f"data: {json.dumps({'type': 'done', 'data': {'processing_time_ms': result.get('processing_time_ms', 0)}})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
