# Geo Agent LangGraph

A small, public geospatial AI agent built to demonstrate **LLM tool use, stateful orchestration, deterministic validation, and bounded failure handling** with real-world APIs.

This is not a generic chatbot. The model does not invent weather, coordinates, elevation, or territorial context. It can request a narrow set of read-only tools, while the surrounding Python/LangGraph workflow controls execution and validates returned data.

## Why this project exists

The project is intentionally small enough to understand end to end. Its goal is to make the architecture behind an agentic workflow visible:

```text
User CLI
   ↓
LangGraph state machine
   ↓
DeepSeek via LangChain
   ↓
Tool calls
   ├── Nominatim → place / coordinates / administrative context
   ├── Open-Meteo → current weather
   └── Open-Meteo → elevation
   ↓
Deterministic Python validation
   ↓
continue / retry once / partial answer
```

The important boundary is that the **LLM proposes actions**, but the **application owns execution, validation, retry limits, and tool permissions**.

## What each AI component does

### LangChain

LangChain provides the model and tool abstractions used by the application. The geospatial functions are exposed as typed tools, and DeepSeek is bound to those tools through the LangChain integration.

### LangGraph

LangGraph owns the workflow state and routing. It controls when the model runs, when tools execute, when results are validated, whether one retry is allowed, and when the workflow must terminate.

### DeepSeek

DeepSeek is the language model. It interprets the user request, decides which available tool to request, consumes tool results, and synthesizes the final answer. It does **not** receive arbitrary HTTP access or permission to call unknown services.

## Tools and data sources

| Tool | Source | Purpose |
| --- | --- | --- |
| `get_territorial_context` | OpenStreetMap Nominatim | Resolve a place name to WGS84 coordinates and administrative context |
| `get_weather` | Open-Meteo Forecast API | Retrieve current weather conditions |
| `get_elevation` | Open-Meteo Elevation API | Retrieve terrain elevation in metres |

All tools use fixed provider URLs and return the same explicit result contract:

```python
{
    "ok": True | False,
    "tool": "tool_name",
    "data": {...} | None,
    "error": "message" | None,
}
```

That contract allows tool output to be checked by normal Python before the workflow continues.

## Validation and failure handling

Validation is deterministic code, not a second LLM prompt.

The application checks, among other things:

- whether a tool explicitly succeeded;
- whether required data is present;
- whether coordinates are inside valid WGS84 ranges;
- whether elevation is numeric;
- whether required current-weather fields exist.

If a tool or provider fails, the graph allows **exactly one workflow retry**. The retry budget is owned by LangGraph state rather than by the model. If the second attempt still fails, or the model does not make a valid retry, the workflow terminates with a partial answer and states which data was unavailable.

## Project structure

```text
src/geo_agent/
├── cli.py
├── graph.py
├── model.py
├── state.py
├── validation.py
└── tools/
    ├── common.py
    ├── territorial.py
    ├── weather.py
    └── elevation.py

tests/
├── test_cli.py
├── test_graph.py
├── test_validation.py
├── test_territorial_tool.py
├── test_weather_tool.py
└── test_elevation_tool.py
```

## Setup

Requires Python 3.11 or newer.

```bash
git clone https://github.com/juanmanueltorres-creator/geo-agent-langgraph.git
cd geo-agent-langgraph
python -m venv .venv
```

Activate the environment.

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install the package and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Create a local `.env` from `.env.example` and add your own DeepSeek API key:

```text
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-v4-flash
```

`.env` is ignored by Git and must never be committed.

## Run

After installation:

```bash
geo-agent "Analyze Córdoba, Argentina using current weather, elevation and territorial context"
```

A run may look conceptually like this:

```text
User question
    ↓
get_territorial_context("Córdoba, Argentina")
    ↓
coordinates
    ↓
get_weather(latitude, longitude)
get_elevation(latitude, longitude)
    ↓
validation
    ↓
final grounded answer
```

The CLI also prints the tool names that were actually executed, making the orchestration visible instead of hiding it behind a chatbot response.

## Tests

The automated suite does **not** require internet access or a DeepSeek API key. External HTTP responses and model behavior are replaced with controlled test doubles.

```bash
python -m pytest -v
```

The suite covers:

- package and CLI validation;
- Nominatim success, missing locations, identifiable User-Agent, and process-local caching;
- Open-Meteo weather and elevation parsing;
- deterministic result validation;
- model → tool → validation → model routing;
- successful tool execution;
- exactly one retry after a failed tool result;
- forced partial termination when the retry cannot recover.

GitHub Actions runs the same suite on Python 3.11 and also compiles the package source.

## Security boundaries

The v0 agent deliberately has a small capability surface:

- tools are read-only;
- the model cannot choose arbitrary URLs;
- credentials are loaded only from the local environment;
- public API responses are treated as untrusted data and normalized;
- no database writes or destructive operations exist;
- retry behavior is bounded to prevent uncontrolled loops.

## Nominatim usage

The public Nominatim service is used conservatively. The tool sends an identifiable application User-Agent, throttles requests to at most one per second, and caches repeated place queries for the lifetime of the Python process. This repository is not intended to provide bulk geocoding.

## Limitations

This is an intentionally narrow v0 learning/portfolio project, not a production geospatial platform.

It does not currently include:

- FastAPI or a hosted HTTP API;
- PostgreSQL/PostGIS persistence;
- long-term conversation memory;
- RAG or a vector database;
- MCP;
- multi-agent coordination;
- user authentication;
- human approval checkpoints;
- GeoPlatform integration;
- managed observability.

The automated suite verifies orchestration without paid API calls. A real end-to-end smoke test requires the developer to supply their own `DEEPSEEK_API_KEY` locally.

## Roadmap

- **v0.2** — FastAPI interface and an explicit human-approval checkpoint for selected actions.
- **v0.3** — expose selected geospatial capabilities through MCP.
- **v0.4** — optional PostgreSQL/PostGIS persistence for execution traces and spatial context.

Each iteration should remain independently understandable and testable.

## Attribution

Geocoding and administrative context use **OpenStreetMap Nominatim** data. © OpenStreetMap contributors.

Weather and elevation data are provided through **Open-Meteo**. Open-Meteo weather data incorporates datasets from national weather services and other meteorological providers; see the Open-Meteo documentation for provider-specific attribution requirements.

## License

MIT License. See `LICENSE`.
