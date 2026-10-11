"""Stretch placeholder for market data integrations.

No live or mock market feed is configured; this client reports an explicit
error so callers cannot mistake an unsupported request for empty evidence.
"""
from mcp.result import ToolResult


def _not_implemented(tool: str) -> ToolResult:
    return {"status": "error", "mock": False, "items": [], "error": f"{tool} is not implemented"}


def get_stock_price(symbol: str) -> ToolResult:
    return _not_implemented("get_stock_price")


def get_fx_rate(base: str, quote: str) -> ToolResult:
    return _not_implemented("get_fx_rate")


def get_commodity_price(commodity: str) -> ToolResult:
    return _not_implemented("get_commodity_price")


def get_market_news(query: str) -> ToolResult:
    return _not_implemented("get_market_news")
