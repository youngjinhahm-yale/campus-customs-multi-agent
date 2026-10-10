"""What defines one agent role: its prompt file, its MCP tool allowlist, its output."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import AgentName

# Every agent can read the ticket it is working and the shop's 'today'.
COMMON_TOOLS = frozenset({"get_ticket", "get_shop_date"})


@dataclass(frozen=True)
class AgentSpec:
    name: AgentName
    description: str          # shown to teammates so they know whom to delegate to
    prompt_file: str          # file in backend/prompts/
    mcp_tools: frozenset[str]
    output_type: type
