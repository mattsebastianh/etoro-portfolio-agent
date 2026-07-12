# eTRADER — eToro Portfolio Agent

Claude Code project: a personal eToro portfolio agent backed by a local Python
MCP server that wraps the eToro Public API.

## Role

At the start of every session, read `agent instruction/etoro-trader-project-instructions.md`
and operate as **eTRADER** as defined there: portfolio tracking, monitoring, analysis,
risk management, and confirmation-gated trade execution. The hard guardrails in that
file (confirmation gate, demo-first, stop-loss required, position-sizing limits) are
non-negotiable.

## Project layout

| Path | Purpose |
|---|---|
| `agent instruction/etoro-trader-project-instructions.md` | The eTRADER role definition — read first |
| `etoro-mcp/` | Python MCP server (stdio) wrapping the eToro Public API |
| `etoro-mcp/.venv/` | Dedicated virtualenv for the server (Python 3.14) |
| `.mcp.json` | Project-scoped MCP config for Claude Code — **contains API keys, never commit** |
| `.mcp.json.example` | Key-free template of the above |
| `memory/` | Agent memory: one fact per file, indexed in `memory/MEMORY.md` |
| `install-etoro-mcp.sh` | Installer: venv + deps + `.mcp.json` |

## MCP configuration

The `etoro` server is registered at **project scope** via `.mcp.json` in the project
root (Claude Code's default project-scope path). It launches
`etoro-mcp/.venv/bin/python3 etoro-mcp/server.py` with env vars:

- `ETORO_API_KEY` / `ETORO_USER_KEY` — credentials (demo-environment keys)
- `ETORO_MODE` — `demo` or `real`
- `ETORO_ENABLE_TRADING` — `true` enables the trading tools

To change mode or trading, edit `.mcp.json` and restart the Claude Code session.
Check server status with `claude mcp list` or `/mcp`.

## Session protocol

1. Read the agent instructions, then check `memory/MEMORY.md` for known bugs,
   pending alerts, and validated fixes before calling MCP tools.
2. Announce the active mode (`[DEMO]` / `[REAL]`) — infer it from `.mcp.json`.
3. New durable facts (bugs found, alert levels the user sets, validated workarounds) go
   into `memory/` as a new file plus an index line in `memory/MEMORY.md`.

## Conventions

- Never print the API keys in output; refer to them by env var name.
- Server code changes: `etoro-mcp/server.py` is the single source; restart the
  session after edits so the server reloads.
- Dependencies are pinned in `etoro-mcp/requirements.txt`; install into
  `etoro-mcp/.venv` with `.venv/bin/python3 -m pip` (not the `pip` wrapper script).
