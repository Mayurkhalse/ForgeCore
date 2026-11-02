# Antigravity Technical Notes (Milestone 0)

This document records the verified configuration paths, formats, and lifecycle capabilities of Google Antigravity (AGY) relevant to ForgeCore.

---

## 1. MCP Configuration

- **Global Config Path:** `~/.gemini/config/mcp_config.json`
- **Schema:**
  ```json
  {
    "mcpServers": {
      "forgecore": {
        "command": "python",
        "args": ["-m", "forgecore.cli", "serve"],
        "env": {}
      }
    }
  }
  ```
- **Supported Transports:**
  - `stdio`: Local processes communicating over standard input/output.
  - `streamable-http`: Remote endpoints (spec `2025-03-26`). Note: legacy SSE (`2024-11-05`) is not supported without a stdio bridge.
- **Server `instructions` Support:**
  - MCP `initialize` returns `serverInfo`, `capabilities`, and optional `instructions: string`.
  - In Antigravity, MCP tools are automatically discovered and surfaced to the agent.
  - As planned in ForgeCore's 3-channel model, Channel A delivers the Core Contract via `instructions`, Channel B writes the global rule file, and Channel C enforces via deterministic verification.

---

## 2. Global Rules & Guidelines

- **Global Discovery Root:** `~/.gemini/config/`
- **Rule Locations:**
  - Directory-based rules: `GEMINI.md` or `AGENTS.md` in any directory. Walking up from current working directory to the repository root loads all rules.
  - Workspace rules: `.agents/rules/*.md`
  - Global user rules: `~/.gemini/config/GEMINI.md` or `~/.gemini/config/AGENTS.md`
- **Format:** Standard Markdown. Standalone `GEMINI.md` / `AGENTS.md` files apply unconditionally to their directory scope.
- **Budget & Caps:**
  - Per-file limit: 24,000 bytes.
  - Aggregate rules budget: 20,000 tokens (`defaultRulesBudget`).

---

## 3. Lifecycle Hooks

- **Configuration Path:** `~/.gemini/config/hooks.json` (Global) or `.agents/hooks.json` (Workspace).
- **Supported Lifecycle Events:**
  - `SessionStart`: Runs once when a new conversation session starts.
  - `PreInvocation`: Runs before model invocation.
  - `PostInvocation`: Runs after tool calls finish.
  - `PreToolUse`: Runs before a tool executes (grouped with `matcher` regex, e.g. `edit_file`, `write_file`, `run_command`).
  - `PostToolUse`: Runs after a tool completes (grouped with `matcher` regex).
  - `Stop`: Runs when execution loop terminates.
- **Execution Contract:**
  - Command executed via shell (`sh -c` on Unix, `cmd /c` on Windows).
  - Context passed as JSON on `stdin` (camelCase fields like `conversationId`, `stepIdx`, `cwd`).
  - Hook outputs JSON on `stdout`.
  - Can inject reminders, emit warnings, or abort execution.

---

## 4. Path and Platform Nuances

- **Windows vs. POSIX:**
  - On Windows: Home path expands to `C:\Users\<Username>\.gemini\config\`.
  - Config paths must use properly escaped backslashes or forward slashes in JSON.
  - Python execution on Windows may require full path to venv executable (e.g. `C:\Users\...\.venv\Scripts\python.exe` or `python` if installed in PATH).
- **Graceful Degradation:**
  - If MCP instructions are ignored, global `GEMINI.md` rule provides the Core Contract.
  - If agent skips calling tools, `hooks.json` (PostToolUse / Stop) and CI pre-commit hooks can enforce verification deterministically.
