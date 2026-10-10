"""Boss: reads each ticket, decides who works on it, and makes the final call."""

from ..models import TicketResolution
from .spec import COMMON_TOOLS, AgentSpec

SPEC = AgentSpec(
    name="boss",
    description="Reads each ticket, routes work to the right teammates, and makes the final call.",
    prompt_file="boss.md",
    mcp_tools=COMMON_TOOLS | {
        "list_open_tickets",
        "update_ticket",
        "list_payment_requests",
        "list_drafts",
        "get_cash_balance",
    },
    output_type=TicketResolution,
)
