"""Stretch placeholder for company and supplier intelligence integrations."""
from mcp.result import ToolResult


def _not_implemented(tool: str) -> ToolResult:
    return {"status": "error", "mock": False, "items": [], "error": f"{tool} is not implemented"}


def company_profile(company: str) -> ToolResult:
    return _not_implemented("company_profile")


def supplier_lookup(query: str) -> ToolResult:
    return _not_implemented("supplier_lookup")


def get_company_events(company: str) -> ToolResult:
    return _not_implemented("get_company_events")
