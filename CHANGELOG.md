# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); dates are `YYYY-MM-DD`.

## [Unreleased]

## [0.1.0] - 2026-07-12

### Added
- Initial public release: eTRADER agent instructions (confirmation gate,
  demo-first, stop-loss required, position-sizing limits).
- `etoro-mcp/server.py` MCP server (stdio) wrapping the eToro Public API:
  profile, portfolio, PnL, positions, trading history, balances, instrument
  search/lookup, rates, candles, watchlists, price alerts, and opt-in trading
  tools (`create_order`, `close_position`, `cancel_order`, `modify_position`).
- `install-etoro-mcp.sh` installer (venv + pinned deps + `.mcp.json`).
- `memory/` agent memory system for durable facts across sessions.
