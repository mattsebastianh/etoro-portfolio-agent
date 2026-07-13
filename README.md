# eTRADER — eToro Portfolio Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14%2B-blue.svg)](etoro-mcp/requirements.txt)
[![MCP](https://img.shields.io/badge/MCP-stdio%20server-6f42c1.svg)](https://modelcontextprotocol.io)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-project-b16fda.svg)](https://claude.com/claude-code)

A personal eToro portfolio agent for [Claude Code](https://claude.com/claude-code), backed by a local Python MCP server that wraps the [eToro Public API](https://api-portal.etoro.com). Track positions, analyze instruments, manage risk, and execute confirmation-gated trades — all from a Claude Code session.

## How it works

Claude Code loads this project and operates as **eTRADER**, a disciplined portfolio agent defined in [`agent instruction/etoro-trader-project-instructions.md`](agent%20instruction/etoro-trader-project-instructions.md). The agent talks to eToro through a project-scoped MCP server (`etoro-mcp/server.py`, stdio transport) that exposes tools for:

| Skill | Tools |
|---|---|
| Identity | `get_profile` |
| Tracking | `get_portfolio`, `get_positions`, `get_balances`, `get_pnl` |
| History | `get_trading_history` |
| Market data | `search_instruments`, `get_instrument_by_symbol`, `get_instrument_by_id`, `get_rates`, `get_candles` |
| Watchlists & alerts | `get_watchlists`, `add_to_watchlist`, `create_price_alert`, `get_price_alerts` |
| Execution (opt-in) | `create_order`, `close_position`, `cancel_order`, `modify_position` |

## Hard guardrails

These are baked into the agent instructions and are non-negotiable:

- **Confirmation gate** — no order is created, modified, or closed without explicit confirmation of the exact order ticket in the current conversation.
- **Demo-first** — new strategies run in demo mode before real.
- **Stop-loss required** — every new position ships with a stop-loss.
- **Position sizing** — default risk ≤1% of equity per trade; single positions capped at 10% of equity.
- Capital preservation ranks above profit capture. Always.

## Setup

Requirements: Python 3.14+, a Claude Code installation, and eToro API keys (create them in eToro under *Settings → Trading → API Key Management*).

```bash
./install-etoro-mcp.sh
```

The installer creates `etoro-mcp/.venv`, installs pinned dependencies from `etoro-mcp/requirements.txt`, and writes a project-scoped `.mcp.json` from your keys.

Alternatively, copy `.mcp.json.example` to `.mcp.json` and fill it in by hand.

### Configuration (`.mcp.json` env vars)

| Variable | Purpose |
|---|---|
| `ETORO_API_KEY` | Public API key (identifies the app) |
| `ETORO_USER_KEY` | User key from API Key Management |
| `ETORO_MODE` | `demo` or `real` |
| `ETORO_ENABLE_TRADING` | `true` to enable the execution tools |

Change mode or trading by editing `.mcp.json` and restarting the Claude Code session. Verify the server with `claude mcp list` or `/mcp`.

> **`.mcp.json` contains your API keys — it is gitignored and must never be committed.**

## Usage

Start Claude Code in the project directory and talk to it in plain language:

- *"How's my portfolio?"* — snapshot with positions, P&L, and risk flags
- *"Analyze TSLA"* — multi-timeframe technical read with an enter/wait/avoid verdict
- *"Buy $500 of AAPL with a 5% stop"* — presents an order ticket, executes only on your confirmation
- *"Risk check"* — concentration, aggregate risk-at-stop, drawdown protocol
- *"Weekly review"* — win rate, expectancy, and an honest behavioral diagnosis

## Project layout

| Path | Purpose |
|---|---|
| `agent instruction/` | The eTRADER role definition |
| `etoro-mcp/server.py` | The MCP server (single source) |
| `etoro-mcp/requirements.txt` | Pinned dependencies |
| `.mcp.json.example` | Key-free config template |
| `install-etoro-mcp.sh` | One-shot installer |
| `memory/` | Agent memory — one fact per file, indexed in `memory/MEMORY.md` (local-only; see `memory/MEMORY.md.example`) |
| `CHANGELOG.md` | Notable changes, feature by feature |

## Contributing

Issues and PRs are welcome. Please develop against **demo mode** only, never commit `.mcp.json` or any file containing keys, and keep the hard guardrails intact — changes that weaken the confirmation gate or stop-loss requirements won't be merged.

## License

[MIT](LICENSE)

## Disclaimer

This is a personal tool, not financial advice. Trading involves risk of loss; the agent is explicit that markets are probabilistic and never promises profit. Use demo mode first.
