"""
Agent definition for translating natural language → SQL.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools import preload_memory

from google.genai import types

from typing import Optional
import datetime
from dotenv import load_dotenv

load_dotenv()


# -------------------------------------------------------------------
# CALLBACKS
# -------------------------------------------------------------------
async def auto_save_to_memory(callback_context: CallbackContext):
    """Automatically save the session to memory after each agent turn"""
    print("agent callback fired")
    # for inMemory, it replaces the whole session with the new one but for persistent, it uses an llm to extract new important things and merges it with whats already there
    try:
        await callback_context._invocation_context.memory_service.add_session_to_memory(
            callback_context._invocation_context.session
            )
        print("Session saved to memory")
    except Exception as e:
        print(f"Failed to save session to memory: {e}")

    return None # proceed normally even if saved to memory fails


def log_llm_call(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Runs BEFORE every LLM call.

    Useful for:
        - debugging prompts
        - auditing context size
        - blocking invalid requests
    """

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    messages_count = len(llm_request.contents) if llm_request.contents else 0

    print(f"[{timestamp}] LLM call with {messages_count} messages")

    # Safety guard
    if messages_count == 0:

        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text="Blocked: request had no context"
                    )
                ],
            )
        )

    return None


def after_response(
    callback_context: CallbackContext,  # always need to include even if you dont use it
    llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Runs AFTER every LLM response.

    Good place to log token usage.
    """

    if llm_response.usage_metadata:
        usage = llm_response.usage_metadata

        print(
            f"[Tokens] "
            f"input={usage.prompt_token_count} "
            f"output={usage.candidates_token_count}"
        )

    return None


# -------------------------------------------------------------------
# DATABASE SCHEMA
# -------------------------------------------------------------------

SCHEMA = """
Table: movies

Columns:
- id (INTEGER)
- film (TEXT)
- genre (TEXT)
- lead_studio (TEXT)
- audience_score (INTEGER)
- profitability (REAL)
- rotten_tomatoes (INTEGER)
- worldwide_gross (REAL)
- year (INTEGER)
"""

# -------------------------------------------------------------------
# AGENT FACTORY
# -------------------------------------------------------------------

def create_agent() -> Agent:
    """
    Create the SQL translation agent.

    The agent ONLY converts natural language → SQL.
    """

    return Agent(
        name="sql_translator",

        model=Gemini(
            model="gemini-2.5-flash-lite"
        ),

        instruction=f"""
            You are a SQL translation assistant for a movie database.

            Your ONLY job is converting natural language to SQL.

            Database schema:
            {SCHEMA}

            Rules:

            - Output ONLY the SQL query
            - No explanations
            - No markdown
            - Only SELECT statements
            - Only reference the 'movies' table
            - Use LIKE for text comparisons
            - If the question cannot be answered, return exactly:
            CANNOT_TRANSLATE
            """,

        before_model_callback=log_llm_call,
        after_model_callback=after_response,
        after_agent_callback=auto_save_to_memory,
        tools=[preload_memory],   # force the agent to check memory or use load_memory to allow the agent to use memory whenever it thinks you should
    )