# Geo Agent v0 Design

## Purpose

Build a small, public, portfolio-ready geospatial AI agent that demonstrates how an LLM can use real tools inside a controlled stateful workflow. The project is intentionally narrow: one CLI query about a place, three real geospatial tools, explicit validation, bounded retry behavior, and a final grounded answer.

The goal is to learn and demonstrate the architecture behind LangChain/LangGraph agentic workflows without coupling the project to GeoPlatform or adding unrelated infrastructure.

## User Experience

The v0 interface is a command-line program.

Example:

```bash
geo-agent "Analyze Córdoba, Argentina"
```

The CLI will show the tools used and then a concise final answer grounded in the returned API data.

A typical run should conceptually follow:

```text
User question
    ↓
LangGraph state machine
    ↓
DeepSeek via LangChain
    ↓
get_territorial_context("Córdoba, Argentina")
    ↓
coordinates + administrative context
    ↓
get_weather(lat, lon)
get_elevation(lat, lon)
    ↓
validation
    ↓
additional tool call or bounded retry if needed
    ↓
final synthesis
```

## Technology

- Python 3.11+
- LangChain for model/tool abstractions and message handling
- `langchain-deepseek` as the provider-specific LangChain integration
- LangGraph for explicit stateful orchestration and conditional routing
- DeepSeek API, default model `deepseek-v4-flash`
- HTTPX for external HTTP requests
- Open-Meteo Forecast API for current weather
- Open-Meteo Elevation API for elevation
- OpenStreetMap Nominatim for place geocoding and administrative context
- python-dotenv for local environment loading
- Pytest plus HTTP mocking for automated tests

## Repository Structure

```text
geo-agent-langgraph/
├── src/
│   └── geo_agent/
│       ├── __init__.py
│       ├── cli.py
│       ├── graph.py
│       ├── model.py
│       ├── state.py
│       ├── validation.py
│       └── tools/
│           ├── __init__.py
│           ├── common.py
│           ├── territorial.py
│           ├── weather.py
│           └── elevation.py
├── tests/
│   ├── test_territorial_tool.py
│   ├── test_weather_tool.py
│   ├── test_elevation_tool.py
│   ├── test_validation.py
│   └── test_graph.py
├── docs/superpowers/specs/
├── docs/superpowers/plans/
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

Each module has one responsibility. HTTP/provider details stay inside tools; orchestration stays in `graph.py`; model construction stays in `model.py`; state shape stays in `state.py`; result checking stays in `validation.py`; CLI concerns stay in `cli.py`.

## Model Integration

The only required secret is:

```text
DEEPSEEK_API_KEY=
```

The model name is configurable and defaults to:

```text
DEEPSEEK_MODEL=deepseek-v4-flash
```

No key is committed. `.env` remains ignored and `.env.example` contains names only.

LangChain owns the model abstraction and tool schemas. LangGraph owns the workflow. DeepSeek is the model provider, not the orchestrator.

## Tools

All tools return a common serializable shape:

```python
{
    "ok": True | False,
    "tool": "tool_name",
    "data": {...} | None,
    "error": "message" | None,
}
```

This makes failures explicit and allows deterministic validation outside the LLM.

### `get_territorial_context`

Input:

```python
location: str
```

Responsibility:

- resolve a human place query with Nominatim;
- return latitude and longitude;
- return display name;
- return stable administrative context where available;
- return the OSM/Nominatim place category/type where available.

Nominatim usage rules are treated as product constraints, not suggestions:

- identify the application with a custom User-Agent;
- never exceed one Nominatim request per second;
- cache repeated place queries for the lifetime of the CLI process;
- show OpenStreetMap attribution in README/output documentation;
- do not turn this repo into a generic high-volume geocoding service.

### `get_weather`

Input:

```python
latitude: float
longitude: float
```

Responsibility:

Query Open-Meteo current conditions and return a deliberately small set of fields useful for the demo:

- temperature at 2 m;
- apparent temperature;
- precipitation;
- weather code;
- wind speed at 10 m;
- observation time/timezone when returned.

### `get_elevation`

Input:

```python
latitude: float
longitude: float
```

Responsibility:

Query the Open-Meteo Elevation API and return terrain elevation in metres.

## Agent State

The graph state contains only fields needed by v0:

```text
messages
question
tool_results
errors
retry_count
final_answer
```

`messages` uses LangChain message objects and LangGraph message accumulation. `tool_results` stores normalized tool outputs for deterministic inspection. `errors` records validation/provider failures. `retry_count` is bounded. `final_answer` stores the user-facing synthesis.

No long-term memory, database, embeddings, RAG, conversation persistence, or user accounts are part of v0.

## Graph

The v0 graph has three conceptual nodes:

```text
agent → tools → validate
  ↑              │
  └──────────────┘
```

The `agent` node asks DeepSeek what to do next. If the model emits tool calls, routing sends execution to the tool node. Tool outputs are then passed through deterministic validation before returning to the agent. If the model emits a final response with no tool calls, the graph ends and records `final_answer`.

The model is instructed to ground answers in tool results and to avoid inventing missing measurements.

The graph must support multi-step tool use: for a place-name query, the model can first geocode the place, receive coordinates, and then call weather/elevation tools using those coordinates.

## Validation and Retry

Validation is code, not another model prompt.

A tool result is invalid when:

- `ok` is false;
- required `data` is absent;
- coordinates are outside WGS84 ranges;
- elevation is missing or non-numeric;
- required weather fields are absent.

Provider/network failures are returned as structured tool errors rather than uncaught exceptions.

The graph allows at most one workflow retry after a validation/provider failure. After the retry budget is exhausted, the agent must produce a partial answer that explicitly states what data could not be retrieved. It must not fabricate replacements.

HTTP requests use explicit timeouts. Retry behavior must remain bounded so a CLI invocation cannot loop indefinitely.

## CLI Behavior

The package exposes a `geo-agent` command.

Required behavior:

1. refuse an empty question with a clear local validation message;
2. fail clearly when `DEEPSEEK_API_KEY` is missing;
3. invoke the compiled LangGraph workflow;
4. display the tool names that were actually executed;
5. display the final answer;
6. return a non-zero exit code only for unrecoverable local/setup failures, not for a single unavailable external data source when a partial answer can be produced.

## Testing

Automated tests must not require internet access or a DeepSeek key.

Tests use mocked HTTP responses and a fake model where needed.

Required coverage:

- territorial tool success and no-result/error behavior;
- Nominatim identifiable User-Agent and request throttling/cache behavior;
- weather tool success and malformed/provider failure behavior;
- elevation tool success and malformed/provider failure behavior;
- deterministic validation rules;
- graph routing from model → tools → validation → model;
- bounded retry behavior;
- final response path with no tool call;
- missing-key/empty-query CLI validation where practical.

A separate documented smoke test may call the real public APIs and DeepSeek manually, but it is not part of the automated suite.

## Security and Public-Repo Constraints

- Never commit `.env` or API keys.
- No credentials in tests, fixtures, README examples, logs, or screenshots.
- Public API responses are treated as untrusted input and normalized before use.
- HTTP requests use fixed provider base URLs; the LLM cannot choose arbitrary URLs.
- Tools expose narrow typed arguments rather than generic HTTP access.
- No write-capable external tools exist in v0.

## README Requirements

The README should explain the project as an orchestration demo, not as a generic chatbot.

It must include:

- what LangChain does in this project;
- what LangGraph does in this project;
- what DeepSeek does in this project;
- architecture diagram;
- tool list and data sources;
- setup instructions;
- `.env` example without secrets;
- example CLI run;
- testing commands;
- limitations;
- Open-Meteo/Copernicus and OpenStreetMap attribution;
- a short roadmap.

## Explicit Non-Goals for v0

Do not add the following in v0:

- FastAPI;
- PostgreSQL/PostGIS;
- frontend/UI;
- Docker;
- MCP;
- RAG/vector database;
- multi-agent architecture;
- long-term memory;
- authentication;
- GeoPlatform integration;
- human approval checkpoints;
- LangSmith or paid observability services.

These are potential follow-on iterations only after the CLI workflow is correct and understandable.

## Definition of Done

v0 is complete when a developer can clone the public repo, install dependencies, add only a DeepSeek API key, run one CLI command, observe the agent use real geospatial tools through LangGraph, receive a grounded response, and run the automated test suite without external network access.
