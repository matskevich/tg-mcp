"""Backward-compatible entrypoint for read-focused MCP server.

Use mcp_server_read.py for explicit read-only naming.
"""

from mcp_server_read import mcp


if __name__ == "__main__":
    mcp.run(transport="stdio")
