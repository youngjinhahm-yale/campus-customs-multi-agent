"""Connection to the Campus Customs MCP server.

Every shop fact and every database write goes through this one MCP connection -
the backend has no second shop-tools layer. Each agent sees only the MCP tools on
its allowlist, and no agent ever sees the HUMAN ONLY approval tools.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import FilteredToolset

from .config import MCP_SERVER_SCRIPT, WORKING_DB

# Only a person (through the dashboard/backend endpoint) may call these.
HUMAN_ONLY_TOOLS = frozenset({"approve_payment_request", "reject_payment_request"})


def build_mcp_toolset(db_path: Path = WORKING_DB) -> MCPToolset:
    """Launch mcp_server/server.py over stdio, pointed at the working database.

    FastMCP's stdio transport does not inherit the parent environment, so the DB
    path is passed explicitly.
    """
    env = {**os.environ, "CAMPUS_DB_PATH": str(db_path)}
    transport = StdioTransport(
        command=sys.executable,
        args=[str(MCP_SERVER_SCRIPT)],
        env=env,
        cwd=str(MCP_SERVER_SCRIPT.parent.parent),
    )
    return MCPToolset(transport, id="campus-customs", max_retries=2)


def tools_for(toolset: MCPToolset, allowed: frozenset[str]) -> FilteredToolset:
    leaked = allowed & HUMAN_ONLY_TOOLS
    if leaked:
        raise ValueError(f"Agents may never get human-only tools: {sorted(leaked)}")
    return toolset.filtered(lambda ctx, tool_def: tool_def.name in allowed)
