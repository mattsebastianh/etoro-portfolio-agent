"""
eToro MCP Server
================
MCP server for the eToro Public API (https://api-portal.etoro.com).
Routes verified against the official documentation (2026-07-08).

Required environment variables:
  ETORO_API_KEY     Public API Key (identifies the app)
  ETORO_USER_KEY    User Key (generated in Settings > Trading > API Key Management)
  ETORO_MODE        "demo" | "real"  (default: demo)
  ETORO_ENABLE_TRADING  "true" to enable trading tools (default: false)

Usage: python server.py  (stdio transport)
"""

import os
import uuid
from datetime import date, timedelta
from typing import Any, Optional, Union

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://public-api.etoro.com"

API_KEY = os.environ.get("ETORO_API_KEY", "")
USER_KEY = os.environ.get("ETORO_USER_KEY", "")
MODE = os.environ.get("ETORO_MODE", "demo").lower()  # demo | real
ENABLE_TRADING = os.environ.get("ETORO_ENABLE_TRADING", "false").lower() == "true"

if MODE not in ("demo", "real"):
    raise SystemExit("ETORO_MODE must be 'demo' or 'real'")

mcp = FastMCP("etoro")


def _headers() -> dict[str, str]:
    return {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key": API_KEY,
        "x-user-key": USER_KEY,
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, params: Optional[dict] = None,
                   json: Optional[Union[dict, list]] = None) -> Any:
    if not API_KEY or not USER_KEY:
        return {"error": "ETORO_API_KEY / ETORO_USER_KEY are missing from the environment."}
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        r = await client.request(method, path, params=params, json=json, headers=_headers())
        if r.status_code == 429:
            return {"error": "Rate limit reached (429). Wait before retrying."}
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        if r.status_code >= 400:
            return {"error": f"HTTP {r.status_code}", "detail": data}
        return data


# Info endpoints: /api/v1/trading/info/{mode}/...
def _info_base() -> str:
    return f"/api/v1/trading/info/{MODE}"


# ---------------------------------------------------------------- Identity

@mcp.tool()
async def get_profile() -> Any:
    """Authenticated user's profile (identity)."""
    return await _request("GET", "/api/v1/me")


# ---------------------------------------------------------------- Portfolio & balances

@mcp.tool()
async def get_portfolio() -> Any:
    """Aggregated portfolio snapshot (demo or real mode depending on ETORO_MODE)."""
    return await _request("GET", f"{_info_base()}/aggregate-portfolio")


@mcp.tool()
async def get_pnl() -> Any:
    """Account PnL and portfolio detail (positions, orders, mirrors)."""
    return await _request("GET", f"{_info_base()}/pnl")


@mcp.tool()
async def get_positions() -> Any:
    """Open positions and pending orders (via the PnL endpoint, which includes them)."""
    return await _request("GET", f"{_info_base()}/pnl")


@mcp.tool()
async def get_trading_history(min_date: str = "", page: int = 1, page_size: int = 50) -> Any:
    """History of closed trades. min_date: YYYY-MM-DD (default: 90 days ago)."""
    if not min_date:
        min_date = (date.today() - timedelta(days=90)).isoformat()
    return await _request("GET", f"/api/v1/trading/info/trade/{MODE}/history",
                          params={"minDate": min_date, "page": page, "pageSize": page_size})


@mcp.tool()
async def get_balances() -> Any:
    """Aggregated account balances (cash, margin, equity, PnL).
    Sourced from aggregate-portfolio's accountTotals block — the dedicated
    /api/v1/balances endpoint requires a money.balance:read scope this key
    doesn't have (403), but accountTotals carries the same figures and works
    with the existing demo scopes."""
    data = await _request("GET", f"{_info_base()}/aggregate-portfolio")
    if isinstance(data, dict) and "accountTotals" in data:
        totals = data["accountTotals"]
        return {
            "accountCurrency": data.get("accountCurrency"),
            "availableCash": totals.get("accountAvailableCash"),
            "frozenCash": totals.get("accountFrozenCash"),
            "unrealizedPnl": totals.get("accountCurrentPnl"),
            "totalEquity": totals.get("accountTotalValue"),
            "usedMargin": totals.get("accountTotalUsedMargin"),
            "balance": totals.get("accountBalance"),
            "timestamp": data.get("timestamp"),
        }
    return data


# ---------------------------------------------------------------- Market data

@mcp.tool()
async def search_instruments(query: str, limit: int = 10) -> Any:
    """Search instruments by exact ticker (internalSymbolFull), e.g. 'AAPL', 'BTC'."""
    data = await _request("GET", "/api/v1/market-data/search",
                          params={"internalSymbolFull": query})
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        data["items"] = data["items"][:limit]
    return data


@mcp.tool()
async def get_instrument_by_symbol(symbol: str) -> Any:
    """Resolve a ticker (e.g. 'BTC', 'AAPL') to its Instrument ID and metadata."""
    data = await _request("GET", "/api/v1/market-data/search",
                          params={"internalSymbolFull": symbol})
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        exact = [i for i in data["items"]
                 if str(i.get("internalSymbolFull", "")).upper() == symbol.upper()]
        return exact[0] if exact else {"error": f"No exact match for '{symbol}'",
                                       "candidates": data["items"][:5]}
    return data


@mcp.tool()
async def get_instrument_by_id(instrument_id: int) -> Any:
    """Resolve an Instrument ID (e.g. 1001) to its ticker and metadata."""
    data = await _request("GET", "/api/v1/market-data/search",
                          params={"instrumentId": instrument_id})
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        items = data["items"]
        return items[0] if items else {"error": f"No instrument with id {instrument_id}"}
    return data


@mcp.tool()
async def get_rates(instrument_ids: str) -> Any:
    """Current prices/rates (bid/ask). instrument_ids: comma-separated IDs, e.g. '100000,1001'."""
    ids = [i.strip() for i in instrument_ids.split(",") if i.strip()]
    # eToro's rates endpoint is last-wins on repeated params (returns only the final ID),
    # so fetch each instrument singly and merge — single-ID always works.
    rates = []
    for iid in ids:
        data = await _request("GET", "/api/v1/market-data/instruments/rates",
                              params={"instrumentIds": iid})
        if isinstance(data, dict) and "error" in data:
            return data
        if isinstance(data, dict) and data.get("rates"):
            rates.extend(data["rates"])
    return {"rates": rates}


@mcp.tool()
async def get_candles(instrument_id: int, interval: str = "OneDay", count: int = 30) -> Any:
    """OHLCV candle history (most recent first). interval: OneMinute, FiveMinutes,
    TenMinutes, FifteenMinutes, ThirtyMinutes, OneHour, FourHours, OneDay, OneWeek. count: max 1000."""
    return await _request(
        "GET",
        f"/api/v1/market-data/instruments/{instrument_id}/history/candles/desc/{interval}/{count}")


# ---------------------------------------------------------------- Watchlists

@mcp.tool()
async def get_watchlists() -> Any:
    """List the user's watchlists."""
    return await _request("GET", "/api/v1/watchlists")


@mcp.tool()
async def add_to_watchlist(watchlist_id: str, instrument_ids: list[int]) -> Any:
    """Add instruments to a watchlist (body is an array of item objects)."""
    items = [{"itemId": i, "itemType": "Instrument"} for i in instrument_ids]
    return await _request("POST", f"/api/v1/watchlists/{watchlist_id}/items",
                          json=items)


# ---------------------------------------------------------------- Price alerts

@mcp.tool()
async def create_price_alert(symbol: str, target_price: float) -> Any:
    """Create an eToro price alert; fires when the market BID reaches target_price.
    symbol e.g. 'SPCX'. Requires the etoro-public:price-alerts:write scope on the key."""
    return await _request("POST", "/api/v1/price-alerts",
                          json={"symbol": symbol, "targetPrice": target_price})


@mcp.tool()
async def get_price_alerts() -> Any:
    """List the user's active eToro price alerts."""
    return await _request("GET", "/api/v1/price-alerts")


# ---------------------------------------------------------------- Trading (opcional)

def _exec_base() -> str:
    # demo: /api/v2/trading/execution/demo/... | real: /api/v2/trading/execution/...
    return "/api/v2/trading/execution/demo" if MODE == "demo" else "/api/v2/trading/execution"


def _exec_base_v1() -> str:
    return "/api/v1/trading/execution/demo" if MODE == "demo" else "/api/v1/trading/execution"


if ENABLE_TRADING:

    @mcp.tool()
    async def create_order(instrument_id: int, direction: str, amount: float,
                           symbol: str = "",
                           leverage: int = 1,
                           stop_loss_rate: Optional[float] = None,
                           take_profit_rate: Optional[float] = None) -> Any:
        """Create a market order (v2). direction: 'BUY' or 'SELL'. amount in USD.
        ⚠️ Operates in the environment defined by ETORO_MODE."""
        body: dict[str, Any] = {
            "action": "open",
            "transaction": "buy" if direction.upper() == "BUY" else "sell",
            "instrumentId": instrument_id,
            "orderType": "mkt",
            "leverage": leverage,
            "amount": amount,
            "orderCurrency": "usd",
        }
        if symbol:
            body["symbol"] = symbol
        if stop_loss_rate is not None:
            body["stopLossRate"] = stop_loss_rate
        if take_profit_rate is not None:
            body["takeProfitRate"] = take_profit_rate
        return await _request("POST", f"{_exec_base()}/orders", json=body)

    @mcp.tool()
    async def close_position(position_id: str, instrument_id: int,
                             units: Optional[float] = None) -> Any:
        """Close a position (fully if units=None, partially by units)."""
        body = {"InstrumentId": instrument_id, "UnitsToDeduct": units}
        return await _request(
            "POST", f"{_exec_base_v1()}/market-close-orders/positions/{position_id}",
            json=body)

    @mcp.tool()
    async def cancel_order(order_id: str) -> Any:
        """Cancel a pending order before it executes."""
        return await _request("DELETE", f"{_exec_base_v1()}/orders/{order_id}")

    @mcp.tool()
    async def modify_position(position_id: str,
                              stop_loss_rate: Optional[float] = None,
                              take_profit_rate: Optional[float] = None) -> Any:
        """Modify SL/TP of an open position."""
        body: dict[str, Any] = {}
        if stop_loss_rate is not None:
            body["stopLossRate"] = stop_loss_rate
        if take_profit_rate is not None:
            body["takeProfitRate"] = take_profit_rate
        return await _request("PUT", f"{_exec_base_v1()}/positions/{position_id}", json=body)


if __name__ == "__main__":
    mcp.run(transport="stdio")
