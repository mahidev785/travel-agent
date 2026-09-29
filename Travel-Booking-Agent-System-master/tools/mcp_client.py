"""MCP integration placeholder (Amadeus disabled)."""

from __future__ import annotations

# Set to False so flight nodes automatically bypass external MCP tools
MCP_CONFIGURED = False


async def get_flight_mcp_tools():
    """Returns an empty list since MCP server integration is disabled."""
    return []