from google.adk.a2a.utils.agent_to_a2a import to_a2a
from agents import create_sql_agent

# create agent
sql_agent = create_sql_agent()

# Convert sql agent to a2a application that
#  - serves agent at a2a protocol endpoints
#  - provides auto generated agent card
#  - handles a2a communication
sql_translator_app = to_a2a(
    sql_agent, port=8001
)