# cli.py
"""
CLI entrypoint for the Movies SQL Agent.

Responsibilities:
- Handle user input/output
- Run the ADK agent
- Execute SQL queries
- Manage session + state

The agent itself ONLY translates natural language → SQL.
"""

import asyncio
import sqlite3
from tabulate import tabulate
import time

from db import get_db_connection
from movie_agent.agent import create_agent

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.memory import InMemoryMemoryService

from google.genai.types import Content, Part

from google.adk.plugins.logging_plugin import LoggingPlugin
# -------------------------------------------------------------------
# Constants (avoid hardcoding values throughout the code)
# -------------------------------------------------------------------

APP_NAME = "data_agent"
USER_ID = "1"
SESSION_ID = f"session_{int(time.time())}"  # new session every time


# -------------------------------------------------------------------
# SQL EXECUTION
# -------------------------------------------------------------------

def run_query(conn: sqlite3.Connection, sql: str):
    """
    Execute an SQL query and return the rows.

    This function does NOT format output — it just talks to SQLite.
    """

    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()

    except sqlite3.Error as e:
        print(f"SQL error: {e}\n")
        return []

    except Exception as e:
        print(f"Unexpected error: {e}\n")
        return []

    return rows


# -------------------------------------------------------------------
# AGENT INTERACTION
# -------------------------------------------------------------------

async def translate_to_sql(
    user_query: str,
    runner: Runner,
    session_id: str,
    last_sql: str | None = None,
) -> str:
    """
    Sends a natural language question to the agent and returns SQL.

    We optionally include the previous SQL query in the prompt so the
    agent can handle follow-up questions like:

        "What about romance instead?"
    """

    # Add context if available
    if last_sql:
        user_query = (
            f"Previous SQL query:\n{last_sql}\n\n"
            f"User question:\n{user_query}"
        )

    message = Content(role="user", parts=[Part(text=user_query)])

    try:
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=message
        ):

            # The final event contains the model's answer
            if event.is_final_response() and event.content:

                for part in event.content.parts:
                    if part.text:
                        sql_result = part.text.strip()  # dont stop and return here if you have an after agent calback or youll stop its lifecycle

    except Exception as e:
        print(f"ADK error: {e}\n")

    return sql_result


# -------------------------------------------------------------------
# SESSION SETUP
# -------------------------------------------------------------------

async def get_or_create_session(session_service):
    """
    Load an existing session or create one if it doesn't exist.

    Sessions store:
        - conversation events
        - structured state
    """

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    if not session:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

    return session


# -------------------------------------------------------------------
# AGENT + RUNNER SETUP
# -------------------------------------------------------------------

async def create_runner():
    """
    Builds the ADK execution stack.

    Architecture:

        Runner
        ├── App
        │   └── Agent
        ├── SessionService
        └── MemoryService
    """

    agent = create_agent()

    # Sessions are stored in SQLite so conversations persist (we can resume it)
    # the agent automatically gets the session events (conversation) so it can use it but it doesnt get state. you need to explicitely pass state
    session_service = DatabaseSessionService(
        db_url="sqlite+aiosqlite:///sessions.db"
    )

    # Memory stores sessions for long-term recall
    # Memory stores knowledge extracted from conversations
    # in memory service uses keyword mmatchign but VertexAiMemoryBankService is the persistent memory and that uses semantic search via embeddings
    memory_service = InMemoryMemoryService()

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
        memory_service=memory_service,   # memory is now available to our agent - but we need to give it to the agent
        plugins=[LoggingPlugin()]
    )

    session = await get_or_create_session(session_service)

    return runner, session_service, session


# -------------------------------------------------------------------
# OUTPUT FORMATTING
# -------------------------------------------------------------------

def print_results(rows):
    """Pretty-print SQL results as a table."""

    if not rows:
        print("No matching records\n")
        return

    headers = rows[0].keys()
    data = [list(row) for row in rows]

    print(tabulate(data, headers=headers, tablefmt="rounded_outline"))
    print(f"\n{len(rows)} row(s) returned\n")


# -------------------------------------------------------------------
# CLI LOOP
# -------------------------------------------------------------------

async def main():

    conn = get_db_connection()

    runner, session_service, session = await create_runner()

    print("\nMovies agent ready. Ask a question or type 'exit'.\n")

    while True:

        try:
            user_input = input("ASK> ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        # ------------------------------------------------
        # Retrieve state from the current session
        # ------------------------------------------------

        last_sql = session.state.get("last_sql")

        # ------------------------------------------------
        # Ask the agent to translate to SQL
        # ------------------------------------------------

        sql = await translate_to_sql(
            user_input,
            runner,
            session.id,
            last_sql
        )

        if not sql or sql == "CANNOT_TRANSLATE":
            print("Could not translate query\n")
            continue

        print(f"[DEBUG] SQL → {sql}\n")

        # ------------------------------------------------
        # Execute query
        # ------------------------------------------------

        rows = run_query(conn, sql)

        print_results(rows)

        # ------------------------------------------------
        # Update session state
        # ------------------------------------------------

        session.state["last_sql"] = sql

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())