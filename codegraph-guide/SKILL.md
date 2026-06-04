---
name: codegraph-guide
description: Guide Codex in using CodeGraph MCP for codebase exploration, architecture tracing, caller/callee analysis, impact analysis, and project indexing. Use when the user asks about CodeGraph, codegraph MCP tools, codebase call graphs, code knowledge graphs, or wants faster code navigation and impact analysis with CodeGraph.
---

# CodeGraph Guide

Use this skill to help users install, validate, initialize, and use CodeGraph as a code intelligence layer for Codex.

CodeGraph is an external CLI and MCP server. This skill does not contain CodeGraph itself. It provides the workflow for using it correctly.

## When to Use

Use this skill when the user wants to:

- Configure CodeGraph for Codex or another coding agent.
- Initialize a project with `.codegraph/`.
- Understand whether CodeGraph is suitable for a codebase.
- Use CodeGraph MCP tools for code exploration.
- Analyze callers, callees, call paths, symbol context, or impact radius.
- Reduce broad file reads, grep loops, and exploratory scanning.

Do not use this skill as a replacement for normal implementation work. CodeGraph helps discover and reason about code; it does not validate correctness by itself.

## Prerequisites

Before relying on CodeGraph tools, verify:

1. CodeGraph CLI can run:

```bash
npx -y @colbymchenry/codegraph --version
```

2. The Codex MCP config contains a CodeGraph server.

Recommended Windows-safe stdio config:

```toml
[mcp_servers.codegraph]
command = "cmd"
args = ["/c", "npx", "-y", "@colbymchenry/codegraph", "serve", "--mcp"]
```

3. The target project has been initialized:

```bash
npx -y @colbymchenry/codegraph init -i
```

If the project is not initialized, explain that CodeGraph cannot answer from an index yet and offer to initialize it in the project root.

## Default Workflow

1. Identify the target project root.
2. Check CodeGraph status in that project:

```bash
npx -y @colbymchenry/codegraph status
```

3. If missing, initialize the project:

```bash
npx -y @colbymchenry/codegraph init -i
```

4. After MCP tools are available, prefer CodeGraph for discovery before reading files manually.
5. Use direct source reads only when CodeGraph returns insufficient detail, stale results, or the task requires exact edited file contents.

## Tool Selection Guidance

When CodeGraph MCP tools are available:

- Use `codegraph_explore` for architecture questions, "how does X work", and broad area understanding.
- Use `codegraph_search` when locating a named symbol or file quickly.
- Use `codegraph_callers` when asking "who calls this?"
- Use `codegraph_callees` when asking "what does this call?"
- Use `codegraph_impact` before changing shared symbols or public APIs.
- Use `codegraph_node` when one exact symbol body is needed.
- Use `codegraph_files` to inspect directory/file structure.
- Use `codegraph_status` to check index health and stale files.

Avoid rebuilding CodeGraph's work with repeated grep/read loops unless the index is missing or stale.

## Response Pattern

For CodeGraph-related tasks, report:

- Whether CodeGraph is installed or configured.
- Whether the target project has a `.codegraph/` index.
- Which CodeGraph tool or CLI command is the next useful step.
- Any fallback if MCP tools are not currently exposed in the session.

## Common Issues

### MCP Config Exists but Tools Are Missing

If `config.toml` contains a CodeGraph MCP server but the current session has no CodeGraph tools, likely causes are:

- Codex Desktop needs a full restart.
- The MCP config is valid but not loaded into the current session.
- The Codex CLI used for diagnostics differs from the Desktop runtime.
- The project has not been initialized with `.codegraph/`.

Do not assume CodeGraph is broken until the CLI can be run and the project status is checked.

### `codegraph` Command Is Not on PATH

On Windows, prefer the `npx` form:

```bash
npx -y @colbymchenry/codegraph <command>
```

This avoids depending on a global `codegraph.exe`.

### Project Is Not Initialized

Run:

```bash
npx -y @colbymchenry/codegraph init -i
```

This creates `.codegraph/` and builds the initial local index.

## Safety

- Do not commit `.codegraph/` unless the user explicitly wants that; it is a local index.
- Do not copy CodeGraph source code into a skill repository.
- Link to the upstream project when explaining the external dependency: `https://github.com/colbymchenry/codegraph`.
- Keep CodeGraph guidance focused on discovery, tracing, and impact analysis; use tests, type checks, and linters for correctness validation.
