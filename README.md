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