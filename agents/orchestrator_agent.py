"""Orchestrator agent for getting the SQL query for a users input"""
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents.remote_a2a_agent import (
    RemoteA2aAgent,
    AGENT_CARD_WELL_KNOWN_PATH
)

retry_config = types.HttpRetryOptions(
    attempts=3,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[
        429,    # rate limit
        500,
        503, # service unavailable
        504 # timeout
    ]
)
def create_orchestrator_agent() -> LlmAgent:

    remote_sql_agent = RemoteA2aAgent(
        name="sql_translator_agent",
        description="agent that converts user queries to SQL ones",
        agent_card=f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}"
    )

    return LlmAgent(
        model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
        name="sql_orchestrator_agent",
        description="Routes user questions to a SQL translation agent that generates SQL queries.",
        instruction="""
        You are an orchestrator that converts user questions into SQL queries.

        Workflow:
        1. Send the user request to the SQL agent.
        2. The SQL agent returns a SQL query.

        Final response rules:
        - Your final response MUST contain ONLY the SQL query returned by the tool.
        - Do NOT answer the user's question.
        - Do NOT add explanations.
        - Do NOT add markdown.
        - Do NOT add any text before or after the SQL.
        - Simply repeat the SQL query exactly as returned by the tool or CANNOT_TRANSLATE if the tool returns CANNOT_TRANSLATE
        """,
        tools=[AgentTool(agent=remote_sql_agent)]
    )
 