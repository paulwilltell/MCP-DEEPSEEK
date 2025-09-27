# MCP–DeepSeek Collaboration Host

This project provides a minimal MCP (Model Context Protocol) host runtime that
enables ChatGPT to orchestrate work across specialised connectors.  The initial
connector integrates the DeepSeek API so that generation-heavy subtasks can be
routed from ChatGPT to DeepSeek while ChatGPT retains responsibility for
architecture, validation, and user communication.

## Architecture Overview

The runtime is intentionally modular:

- **Host runtime (`mcp_host.runtime`)** – Maintains global project context,
  registers connectors, and decides which connector should handle each task.
- **DeepSeek connector (`connectors.deepseek`)** – Translates MCP task payloads
  into DeepSeek API requests, normalises responses, and reports authentication or
  validation errors back to the host.
- **Configuration (`config/settings.yaml`)** – Declares connectors, their
  routing rules, and credential sources.
- **CLI (`scripts/run_host.py`)** – Bootstraps the runtime, loads configuration,
  and exposes a simple JSON-based interface for dispatching tasks.

ChatGPT acts as the task manager: it keeps the shared context, breaks down user
requests, and decides when DeepSeek should be invoked.  DeepSeek focuses on
producing code, boilerplate, or content drafts that ChatGPT can refine before
presenting to the end-user.

## Getting Started

### Prerequisites

- Python 3.10+
- A DeepSeek API key with access to the desired models

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

1. Copy `config/settings.yaml` and adjust values as needed.
2. Provide the DeepSeek API key by exporting the `DEEPSEEK_API_KEY` environment
   variable or by replacing `api_key_env` with an inline `api_key` value.
3. (Optional) Extend the `routes` list to describe which MCP task identifiers
   should always be handled by DeepSeek.

Example configuration excerpt:

```yaml
connectors:
  - name: deepseek
    module: connectors.deepseek
    class: DeepSeekConnector
    api_key_env: DEEPSEEK_API_KEY
    routes:
      - generate_backend
      - generate_frontend
```

## Running the Host

Dispatch a single task from a JSON file:

```bash
python scripts/run_host.py --task examples/generate_backend.json
```

Start an interactive loop that accepts JSON payloads on standard input:

```bash
python scripts/run_host.py --interactive
```

Each JSON task payload should resemble the following schema:

```json
{
  "task": "generate_backend",
  "language": "javascript",
  "framework": "express",
  "requirements": ["CRUD for tasks"],
  "prompt": "(Optional) explicit instructions"
}
```

The runtime keeps the result of the most recent subtask in
`context["last_result"]`, enabling multi-step flows in which DeepSeek builds on
previous outputs.

## Collaboration Example

1. **User request**: “Build a task-tracking web app.”
2. **ChatGPT (MCP host)**:
   - Plans system architecture across frontend, backend, and data layers.
   - Delegates API boilerplate generation with a `generate_backend` task.
3. **DeepSeek connector**:
   - Receives the task payload, crafts a DeepSeek prompt, and posts it to the
     `/tasks` endpoint.
   - Returns structured JSON containing generated endpoint stubs.
4. **ChatGPT**:
   - Validates and integrates DeepSeek’s code with the broader scaffold.
   - Communicates progress back to the user and triggers further subtasks as
     necessary (e.g., UI generation, deployment configuration).

## Troubleshooting

- **AuthenticationError** – Ensure the `DEEPSEEK_API_KEY` environment variable is
  set or provide an inline `api_key` in the configuration file.
- **ConnectorError: No connector available** – Confirm the task identifier is
  listed in the `routes` for an existing connector or that at least one
  connector reports support for the task.
- **Invalid JSON response** – Inspect the DeepSeek response payload for errors
  or rate-limit messages.  The connector surfaces malformed responses so they
  can be retried or escalated.

## Extending the Framework

- Add new connectors by implementing the `Connector` protocol and registering
  them in `config/settings.yaml`.
- Augment the routing logic with project-specific heuristics by subclassing
  `HostRuntime` or wrapping it within your orchestration environment.
- Track richer context (e.g., dependency graphs, artifact history) by storing
  additional data in `HostRuntime.context`.

## Testing

The repository ships with unit tests that cover routing behaviour and
DeepSeek connector error handling.  Run them with:

```bash
pytest
```
