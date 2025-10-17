# MCP-DEEPSEEK

## Overview
MCP-DEEPSEEK demonstrates how OpenAI's ChatGPT can orchestrate work that is executed by DeepSeek via the Model Context Protocol (MCP). The repository contains a minimal host that exposes DeepSeek as a tool provider so that ChatGPT can delegate complex, code-oriented tasks while retaining high-level control over planning, validation, and communication with the user.

## System Architecture
- **ChatGPT (Coordinator):** Operates as the primary agent that interacts with end users, interprets requirements, plans solutions, and decides which MCP tools to invoke.
- **MCP Host:** A lightweight server that brokers requests between ChatGPT and downstream connectors such as DeepSeek. It handles capability registration, tool invocation, and streaming of results back to ChatGPT.
- **DeepSeek Connector:** Wraps DeepSeek's API in an MCP-compliant interface. It receives structured tool calls from the host, translates them into DeepSeek API requests, and returns the generated artifacts (code snippets, analyses, files) in a format ChatGPT can consume.
- **Task Workspace:** A shared filesystem or object storage namespace where intermediate artifacts created by DeepSeek are stored. ChatGPT uses MCP file tools to inspect, modify, or validate these artifacts.

The architecture follows a hub-and-spoke pattern: ChatGPT communicates only with the MCP host (the hub), while the host fans out requests to connectors like DeepSeek (the spokes).

## Component Responsibilities
| Component | Responsibilities |
|-----------|------------------|
| ChatGPT | Collect user requirements, decompose work, select tools, review DeepSeek outputs, and provide final responses. |
| MCP Host | Register available connectors, expose their capabilities to ChatGPT, manage sessions, enforce rate limits, and normalize responses. |
| DeepSeek Connector | Authenticate with DeepSeek, translate MCP tool invocations into API calls, stream generated code or documentation, and report status/errors. |
| Workspace | Persist files produced during collaboration, enabling iterative editing and inspection across multiple tool calls. |

## Task Delegation Flow
1. **User Request:** The user describes a task to ChatGPT (e.g., "Build a CRUD task tracker").
2. **Planning:** ChatGPT analyzes the request, outlines subtasks, and determines which parts require DeepSeek's coding assistance.
3. **Tool Invocation:** ChatGPT calls the MCP host's DeepSeek tool with structured prompts (e.g., code generation instructions).
4. **Execution:** The MCP host forwards the request to the DeepSeek connector, which makes the DeepSeek API call and streams outputs back.
5. **Review:** ChatGPT inspects returned artifacts, validates correctness, and may iterate with additional DeepSeek calls or direct edits.
6. **Delivery:** ChatGPT synthesizes the final answer for the user, citing generated files and describing how the task was accomplished.

## Setup Instructions
### 1. Environment Prerequisites
- Node.js 20+ and npm or yarn (for running the MCP host if built with JavaScript/TypeScript).
- Python 3.10+ (if using the Python host variant).
- Git for cloning this repository.
- Access credentials for both OpenAI (ChatGPT) and DeepSeek APIs.

### 2. Configure API Keys
1. Create a `.env` file in the project root.
2. Add the following environment variables:
   ```bash
   OPENAI_API_KEY="sk-..."
   DEEPSEEK_API_KEY="deepseek-..."
   MCP_HOST_PORT=4000
   ```
3. For local development, export these variables in your shell or use a tool like `direnv` or `dotenv` to load them automatically.
4. Ensure your OpenAI account is configured to access the GPT model you intend to use (e.g., `gpt-4.1` or newer) and that your DeepSeek account has sufficient quota.

### 3. Bring Your Own MCP Host Implementation
This repository currently ships documentation only. To experiment with the described workflow you will need to supply your own
MCP host and DeepSeek connector implementation. You can:

- Scaffold a new project (e.g., `npm create`, `pip install mcp`),
- Implement the host responsibilities outlined above, and
- Register a DeepSeek-backed tool that follows the MCP specification.

Once you have a working host, point your MCP-enabled client (such as ChatGPT) at that server and reuse the configuration
guidance from steps 1 and 2.

## End-to-End Example: Building a Task-Tracking App
1. **User Conversation:** The user asks ChatGPT to "Create a full-stack task-tracking app with backend CRUD endpoints and a React frontend."
2. **ChatGPT Planning:** ChatGPT outlines backend, database, and frontend subtasks, determining which steps can leverage DeepSeek.
3. **Backend Generation:** ChatGPT invokes the DeepSeek `generate_code` tool with instructions to scaffold an Express.js API with task CRUD routes. DeepSeek returns code files saved to the workspace (e.g., `server/index.ts`).
4. **Frontend Generation:** ChatGPT makes another DeepSeek call to produce React components (`TaskList.tsx`, `TaskForm.tsx`) and integrates them with an API client.
5. **Integration Review:** ChatGPT reads the generated files through MCP file tools, runs automated tests or linting if available, and patches minor issues directly.
6. **Deployment Guidance:** ChatGPT prepares deployment instructions and environment configuration notes for the user, referencing the generated artifacts.
7. **Final Response:** ChatGPT summarizes the deliverables, cites file locations, and explains how DeepSeek contributed to the build.

This workflow highlights how ChatGPT delegates intensive coding tasks to DeepSeek while maintaining oversight and delivering a coherent solution.

## Troubleshooting
- **Connection Errors:** Verify that the MCP host is running and reachable on the configured port. Ensure no firewall or VPN rules block local connections.
- **Authentication Failures:** Double-check API keys in `.env` and confirm they are loaded into the runtime environment. Regenerate keys if necessary.
- **Rate Limits or Quota Exhaustion:** Monitor usage dashboards for OpenAI and DeepSeek. Implement exponential backoff in the connector or schedule work during off-peak hours.
- **Schema Mismatches:** If DeepSeek API responses change, update the connector's response parsing logic and re-run tests.
- **Timeouts:** Increase MCP host timeouts for long-running generation tasks and ensure the host streams partial outputs to keep the session alive.

## Extending the Framework
- **Add New Connectors:** Implement additional MCP tools that wrap other APIs (e.g., GitHub Copilot, internal microservices). Register them in the host alongside DeepSeek.
- **Custom Tooling Pipelines:** Chain multiple connectors so ChatGPT can orchestrate linting, testing, or deployment after DeepSeek generates code.
- **Enhanced Observability:** Integrate logging, tracing, and metrics exporters (e.g., OpenTelemetry) to monitor latency and error rates across connectors.
- **Security Hardening:** Add request validation, rate limiting, and audit logging to the MCP host before exposing it in production environments.
- **Workspace Integrations:** Plug in storage providers (S3, GCS, local FS) or Git automations so artifacts can be versioned and shared across sessions.

By expanding the MCP host with additional connectors and tooling, you can evolve MCP-DEEPSEEK into a comprehensive platform for AI-assisted development workflows.
