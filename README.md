1. read files from csv and print to db


# Session
# ├── Events  → [ user said X, agent said Y, tool returned Z, ... ]
# └── State   → { "user:name": "Sam", "query_count": 3 }

the runner automatically passes the session to the model as context
state is structured memory
storage servicce is like a database for your conversations and sessions

the runner connects everything 
- loads sessions
- adds conversation history
- manages tools

the memory is passed to the model in the request every time - ALL OF IT  so you can imagine it gets very big after time so that swhy we use compaction

# When saving things to tool_context.state, the notebook uses prefixes like user:name or app:setting
eg
tool_context.state["user:name"] = "Sam"    # specific to this user
tool_context.state["app:version"] = "1.0"  # shared across all users
tool_context.state["temp:last_sql"] = sql  # only needed briefly

# Compaction automatically summarises old history into a single compressed event every N turns

✅ What to add to YOUR project
Two things are worth adding — both are small changes:
1. Switch to DatabaseSessionService so your sessions survive restarts. One line change.
2. Save the last SQL to state so the agent has context between turns — e.g. "show me more like that last result."

## Memory
The core idea: Sessions vs Memory
Think of it like your own brain:

Session = short-term memory. What you remember from this conversation. Gone when the conversation ends.
Memory = long-term memory. What you remember across all conversations. Persists forever.

The 3-step workflow
Every memory implementation follows the same pattern:
1. INGEST   → take a finished session, push it into memory storage
2. STORE    → memory service holds it (in RAM or cloud)
3. RETRIEVE → agent searches memory when it needs something

Two ways the agent retrieves memory
load_memory — reactive. The agent decides when to search. More efficient, but it might forget to look.
preload_memory — proactive. Memory is automatically searched and injected before every single turn. Always available, but wasteful if the user is just asking something unrelated.

Callbacks — the important new concept
A callback is a function that ADK automatically calls at specific moments in the agent's lifecycle — before/after a turn, before/after a tool call, before/after an LLM call, etc.
User sends message
    → before_agent_callback fires   ← you can inject things here
    → agent thinks + responds
    → after_agent_callback fires    ← you can save things here
The key one for memory is after_agent_callback — it fires after every response, and you can use it to automatically save the session to memory. No manual calls needed.

Memory Consolidation (the production concept)
InMemoryMemoryService just stores raw conversations as-is — every message, word for word.
The production version (VertexAiMemoryBankService) is smarter — it uses an LLM to extract key facts from conversations before storing them. So instead of storing 50 messages, it stores "user is allergic to peanuts, prefers action movies, name is Sam". Much leaner and more useful.

memory is long term storaeg and remembers across sessions

inMemoryMemoryService is a simple keyword search eg:
memory: "users fave colour is blue"
search: favourite colour
result: blue

Production memory systems

More advanced ones:

Vertex AI Memory
Vector databases
Embeddings
Semantic search


## callbacks
| Feature             | Model Callback   | Agent Callback |
| ------------------- | ---------------- | -------------- |
| Access model input  | ✅                | ✅              |
| Access model output | ✅                | ✅              |
| See tokens          | ✅                | ❌              |
| See tool execution  | ❌                | ✅              |
| See reasoning steps | ❌                | ✅              |
| Access agent state  | ❌                | ✅              |
| Access memory store | only if injected | ✅              |
| Scope               | single LLM call  | full agent run |

Agent callbacks (before/after_agent_callback) — wrap the entire cycle including all LLM calls, tool calls, and sub-agents. Use for things that care about the whole job — before for gating the turn (auth checks, injecting user preferences into state), after for finalising it (saving session to memory, audit logging, cleanup).
Model callbacks (before/after_model_callback) — fire every time Gemini specifically is called, which can be multiple times per turn if tools are involved. Use for things specific to the LLM call itself — before for logging what's being sent, caching (return a cached response to skip the API call entirely), or prompt guardrails. after for token counting per-call, content filtering, or normalising the response format.
Tool callbacks (before/after_tool_callback) — fire around each individual tool execution. Use for things about controlling tools specifically — before for validating the arguments Gemini generated, permission checks on specific tools, or short-circuiting with a cached result. after for logging what the tool returned, sanitising the result before it goes back to Gemini, or recording tool usage for billing and auditing.

6.5 How often should you save Sessions to Memory?¶
Options:

Timing	Implementation	Best For
After every turn	after_agent_callback	Real-time memory updates
End of conversation	Manual call when session ends	Batch processing, reduce API calls
Periodic intervals	Timer-based background job	Long-running conversations

### consolitdation
7.3 How Consolidation Works (Conceptual)¶
The pipeline:

1. Raw Session Events
   ↓
2. LLM analyzes conversation
   ↓
3. Extracts key facts
   ↓
4. Stores concise memories
   ↓
5. Merges with existing memories (deduplication)


7.4 Next Steps for Memory Consolidation¶
💡 Key Point: Managed Memory Services handle consolidation automatically.

You use the same API:

add_session_to_memory() ← Same method
search_memory() ← Same method
The difference: What happens behind the scenes.

InMemoryMemoryService: Stores raw events
VertexAiMemoryBankService: Intelligently consolidates before storing


## logging
you can use googles logging plugin for automatic logging
you attatch it to the runner and since the runner controls the entire execution lifecycle, the plugin can observe absolutely everything that happens

the plugin contains its own callbacks like for after and before models, agents and errors but unlike your callbacks that you wrote, you dont need to define custom ones for each agent or attatch it to the agent

this is good for generic logging and tracing

it writes logs uising pythongs standard logging system

it logs:
Typical things it logs include:

user messages

LLM requests

LLM responses

tool calls

execution time

errors

• It works for all agents

Because it’s attached to the runner, every agent run automatically gets logged.


## evaluation
use adk eval cli command.
1) Create an evaluation configuration - define metrics or what you want to measure 2) Create test cases - sample test cases to compare against 3) Run the agent with test query 4) Compare the results
make sure you have the agent assigned to root agent in the file for evaluation

command:
`adk eval movie_agent movie_agent/integration.evalset.json --config_file_path=movie_agent/test_config.json --print_detailed_results`

output:
```
Eval Set Id: sql_automation_integration_suite
Eval Id: sex_and_the_city_genre
Overall Eval Status: PASSED
---------------------------------------------------------------------
Metric: response_match_score, Status: PASSED, Score: 0.9090909090909091, Threshold: 0.8
---------------------------------------------------------------------
Invocation Details:
+----+------------------------+--------------------------+--------------------------+-----------------------+---------------------+------------------------+
|    | prompt                 | expected_response        | actual_response          | expected_tool_calls   | actual_tool_calls   | response_match_score   |
+====+========================+==========================+==========================+=======================+=====================+========================+
|  0 | Whats the genre of the | SELECT genre FROM movies | SELECT genre FROM movies |                       |                     | Status: PASSED, Score: |
Overall Eval Status: PASSED
---------------------------------------------------------------------
Metric: response_match_score, Status: PASSED, Score: 0.9090909090909091, Threshold: 0.8
---------------------------------------------------------------------
Invocation Details:
+----+------------------------+--------------------------+--------------------------+-----------------------+---------------------+------------------------+
|    | prompt                 | expected_response        | actual_response          | expected_tool_calls   | actual_tool_calls   | response_match_score   |
+====+========================+==========================+==========================+=======================+=====================+========================+
|  0 | Whats the genre of the | SELECT genre FROM movies | SELECT genre FROM movies |                       |                     | Status: PASSED, Score: |
|    | movie sex in the city? | WHERE film LIKE "Sex and | WHERE film LIKE '%sex in |                       |                     | 0.9090909090909091     |
|    |                        | the City"                | the city%'               |                       |                     |                        |
+----+------------------------+--------------------------+--------------------------+-----------------------+---------------------+------------------------+
```


## a2a
creates server file for the sql agent cause we want to create an a2a app to serve the agent.

uvicorn

This is the ASGI server that runs your FastAPI / A2A app.

It serves your application over HTTP so other services (like your coordinator) can call it.

2. What to_a2a() actually does

This function automatically creates:

Endpoint	Purpose
/a2a	Main protocol endpoint
/.well-known/agent-card.json	Metadata about the agent
internal message routing	Handles requests/responses

you can see the agent card here:
http://localhost:8001/.well-known/agent-card.json

```
uvicorn sql_agent_server:sql_translator_app --port 8001                                                             
```
> If your running it locallyy run the server in command prompt or something because the debugger keeps disconnecting it
Simple explanation of your design

run your cli as normal like 
```
python cli.py
```

Create the SQL agent

You first build a normal ADK agent that converts natural language into SQL queries.

Convert the SQL agent into an A2A server

Using to_a2a() you wrap the SQL agent in an A2A-compatible web application.

This does three things automatically:

exposes HTTP endpoints for agent communication

generates an Agent Card (/.well-known/agent-card.json) describing the agent

handles the A2A protocol messaging

So now the SQL agent runs as a remote service.

Create a RemoteA2AAgent (client-side proxy)

In your main application you create:

RemoteA2AAgent

This acts as a local proxy object that knows how to talk to the remote A2A agent.

It does this by reading the Agent Card, which tells it:

the agent name

what it does

where the A2A endpoint is

Add the proxy to the orchestrator as a tool/sub-agent

You pass the RemoteA2AAgent into your orchestrator:

AgentTool(agent=remote_sql_agent)

From the orchestrator’s perspective, it behaves just like a normal local agent.

Runtime flow

When a user asks a question:

User
 ↓
Orchestrator Agent
 ↓
RemoteA2AAgent (proxy)
 ↓
HTTP request
 ↓
A2A SQL Agent Server
 ↓
SQL Agent

The response then flows back the same way.

SQL Agent
 ↑
A2A server
 ↑
RemoteA2AAgent
 ↑
Orchestrator

Movies NL-to-SQL AgentA conversational CLI agent that translates natural language questions into SQL queries against a local movies database, built with Google ADK and Gemini.Architecture