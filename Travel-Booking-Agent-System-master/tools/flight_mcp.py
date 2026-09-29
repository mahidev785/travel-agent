"""Flight tools helper (Amadeus MCP integration disabled)."""

from __future__ import annotations

# Set to False so flight nodes automatically fall back to mock data / local tools
MCP_CONFIGURED = False


async def get_flight_mcp_tools():
    """Return empty tools list so the graph falls back to local tools."""
    return []