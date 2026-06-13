"""
LLM Prompt templates.
All prompts for intent classification, SQL generation, repair, and response formatting.
"""

INTENT_CLASSIFICATION = """You are an intent classifier for a data analytics chatbot.
The user has uploaded Excel/CSV files and is asking questions about their data.

Classify the user's question into exactly ONE category:

- SQL_ANALYTICS: Questions that require counting, filtering, grouping, averaging, ranking, summing, comparing, or any data calculations. Examples: "How many?", "Average salary", "Top 10", "Count of", "Total", "List all where", "Compare", "Trend"
- METADATA: Questions about what data is available, what tables exist, what columns are in a table, schema questions. Examples: "What tables do I have?", "Show me the columns", "What data is available?"
- GREETING: Greetings, help requests, or general conversation. Examples: "Hello", "Help", "What can you do?"

IMPORTANT: If the user's question is a follow-up that refers to the previous conversation
(e.g. "show me more", "filter that", "break it down", "what about X?"), use the conversation
history below to understand what they are referring to and classify accordingly.

Available tables and their columns:
{schema_context}

Previous conversation (for context):
{conversation_history}

User question: {question}

Respond with ONLY a JSON object:
{{"intent": "SQL_ANALYTICS" or "METADATA" or "GREETING", "confidence": 0.0-1.0, "reason": "brief explanation"}}"""


TABLE_SELECTION = """You are a data analyst. Given the user's question and the available tables, select which tables are needed to answer the question.

If the question is a follow-up referring to the previous conversation, use the history to
understand which tables were being discussed.

Available tables:
{table_summaries}

Previous conversation (for context):
{conversation_history}

User question: {question}

Respond with ONLY a JSON object:
{{"tables": ["table_name1", "table_name2"], "reason": "brief explanation"}}"""


SQL_GENERATION = """You are a DuckDB SQL expert. Generate a SQL query to answer the user's question.

IMPORTANT RULES:
1. Use DuckDB SQL dialect (very similar to PostgreSQL).
2. ONLY generate SELECT queries. Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE.
3. Always quote table and column names with double quotes if they contain special characters.
4. Use the exact table and column names provided below.
5. If unsure about a column name, use the semantic dictionary hints.
6. For text/categorical filters, use ONLY values that appear in the "allowed values"
   list for that column. Match them exactly. If the user's term is an abbreviation or
   synonym (e.g. a business-unit code), map it to the closest allowed value.
7. SEMANTICS OF STATUS / WORKFLOW COLUMNS:
   - Columns describing a state, status, stage or workflow step usually contain BOTH
     active and terminal (finished) values.
   - "Open" / "active" / "live" / "vacant" / "to be filled" items EXCLUDE terminal
     states. Treat values meaning cancelled, withdrawn, rejected, closed, filled,
     hired, completed, lost or declined as NOT open (these are terminal/finished).
   - Paused-but-not-finished states such as "on hold", "published", "draft",
     "planning", "in progress", "pending" etc. ARE still open (the position has not
     been filled or cancelled yet), so INCLUDE them when counting open items.
   - "Closed" / "completed" / "finished" items mean ONLY those terminal states.
   - Decide which allowed values are open vs terminal from their wording, then filter
     with an explicit IN / NOT IN list of the exact allowed values.
8. When the user asks "how many open ..." (or similar) and a status/workflow column
   exists, prefer returning a BREAKDOWN: GROUP BY that status column with a COUNT(*),
   keeping ONLY the open statuses, ordered by count descending. This shows the
   composition rather than a single ambiguous number. Use a plain COUNT only when the
   user clearly wants a single total.
9. Do NOT sum opening/headcount columns to answer "how many open positions" unless the
   user explicitly asks about number of openings/headcount — count requisitions/rows
   per status instead.
10. FOLLOW-UP QUESTIONS: If the user's question references the previous conversation
    (e.g. "show me more details", "filter that by department", "now break it down by
    region", "what about the top 5?"), use the conversation history below to understand
    what data/table/query they are referring to and generate the appropriate SQL.

Available schema:
{schema_context}

Relationships between tables:
{relationships}

Semantic hints (columns that mean the same thing):
{semantic_hints}

Previous conversation (for context):
{conversation_history}

User question: {question}

Respond with ONLY a JSON object:
{{"sql": "SELECT ...", "explanation": "brief explanation of what this query does"}}"""


SQL_REPAIR = """The SQL query you generated failed with an error. Fix it.

Original question: {question}

Schema context:
{schema_context}

Failed SQL:
{failed_sql}

Error message:
{error}

Generate a corrected query. Respond with ONLY a JSON object:
{{"sql": "SELECT ...", "explanation": "what was wrong and how you fixed it"}}"""


RESPONSE_FORMAT = """You are a helpful data analyst assistant. Given the user's question, the SQL query that was executed, and the results, provide a clear and helpful natural language response.

Previous conversation (for context):
{conversation_history}

User question: {question}

SQL query executed:
{sql}

Query results (as table):
{results}

Row count: {row_count}

Instructions:
- Provide a direct, conversational answer to the question.
- If this is a follow-up question, relate your answer to the previous conversation context.
- Reference specific numbers from the results.
- If the results have multiple rows (e.g. a breakdown / group-by), render them as a
  GitHub-flavored Markdown table with a header row, then add a short one-line summary
  (such as the total) below the table.
- Format numbers nicely (use commas for thousands).
- Be concise but complete.
- If the query returned no results, say so clearly.
- Do NOT include the SQL query in your response unless the user asked for it."""


METADATA_RESPONSE = """You are a helpful data analyst assistant. The user is asking about their uploaded data.

Previous conversation (for context):
{conversation_history}

Available data:
{metadata}

User question: {question}

Provide a clear, helpful response describing the available data. Be specific about table names, column names, row counts, and data types."""

