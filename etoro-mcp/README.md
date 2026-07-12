# eToro MCP Server

MCP server (stdio) for the eToro Public API. Tools: profile, portfolio, PnL,
positions, trading history, balances, instrument search, prices, candles,
watchlists, price alerts and (optional) trading.

## 1. Getting your keys

1. On eToro web: **Settings > Trading > API Key Management > Create New Key**.
2. Choose the environment (**Demo** or **Real** — one key per environment) and
   permissions (**Read** or **Write**).
3. Verify via SMS and copy your **User Key**.
4. Get the **Public API Key** from the developer portal (api-portal.etoro.com).

Note: your account must be verified for the API key option to appear.

## 2. Installation

From the project root, the installer creates the venv, installs the pinned
dependencies, and writes the Claude Code MCP config:

```bash
./install-etoro-mcp.sh
```

Or manually:

```bash
cd etoro-mcp
python3 -m venv --clear .venv
.venv/bin/python3 -m pip install -r requirements.txt
```

Always use `.venv/bin/python3 -m pip` rather than the `pip` wrapper script —
the wrapper hardcodes the venv's absolute path and breaks if the folder is
ever moved or copied (`--clear` also rebuilds it).

## 3. Configuration (Claude Code)

The server is registered at **project scope** via `.mcp.json` in the project
root — the default path Claude Code reads when starting in this folder. Copy
the template and fill in your keys:

```bash
cp .mcp.json.example .mcp.json   # then edit and add your keys
```

Format:

```json
{
  "mcpServers": {
    "etoro": {
      "type": "stdio",
      "command": "/absolute/path/etoro-mcp/.venv/bin/python3",
      "args": ["/absolute/path/etoro-mcp/server.py"],
      "env": {
        "ETORO_API_KEY": "your_public_api_key",
        "ETORO_USER_KEY": "your_user_key",
        "ETORO_MODE": "demo",
        "ETORO_ENABLE_TRADING": "false"
      }
    }
  }
}
```

You can also use the CLI (with `--scope project` it writes the same `.mcp.json`):

```bash
claude mcp add etoro --scope project -e ETORO_API_KEY=... -e ETORO_USER_KEY=... -e ETORO_MODE=demo -- /path/etoro-mcp/.venv/bin/python3 /path/etoro-mcp/server.py
```

Verify with `/mcp` inside a session or `claude mcp list`. After editing
`.mcp.json` or `server.py`, restart the session. `.mcp.json` contains your
keys and is gitignored — never publish it. Claude Code will prompt you to
approve the project server on first use.

## 4. Security

- ALWAYS start with `ETORO_MODE=demo`, a Demo key, and Read permissions.
- Set `ETORO_ENABLE_TRADING=true` only once everything is validated; it
  requires a key with Write permission.
- Consider an IP whitelist and an expiration date when generating the key.
- Rate limits: most endpoints share a 60 req/60s quota; market data 120/60s;
  trading 20/60s.

## 5. Official alternative

eToro publishes a live-documentation MCP at `https://api-portal.etoro.com/mcp`
(useful for looking up endpoints). This server, by contrast, executes real
calls against your account.

## 6. Verifying endpoint paths

Paths are based on the public documentation; if an endpoint returns 404,
check the exact route against the official OpenAPI spec:
`https://api-portal.etoro.com/api-reference/openapi.json`

## 7. Known eToro API quirks (validated against the live API)

- **Rates endpoint is last-wins for multiple IDs.** Passing several
  instrument IDs (comma-joined → HTTP 500; repeated params → only the final
  ID is returned). The server therefore fetches per-ID and merges — fine
  under the 120 req/60s market-data quota.
- **Watchlist writes need item objects, not bare IDs.** The official docs
  show `[1001,1002]` as the POST body, but that yields HTTP 422
  ("Items list … null or empty"). The correct body is
  `[{"itemId": 1001, "itemType": "Instrument"}]`, which the server sends.
  A duplicate add returns 422 by design.
- **Price alerts are unavailable to demo keys.** `/api/v1/price-alerts`
  requires an `etoro-public:price-alerts:*` scope that the key generator
  does not offer for demo keys — the endpoints 403 regardless of settings.
  The tools exist and are correct; set alerts in the eToro app instead.
- **Reverse ID→ticker lookup uses the singular `instrumentId` param** on
  `/api/v1/market-data/search` (the plural `instrumentIds` 404s). This is
  what `get_instrument_by_id` wraps.
- **Direct scripting note:** requests without a browser-like client can be
  Cloudflare-blocked (403, error code 1010) — `httpx` works, plain
  `urllib` does not.
