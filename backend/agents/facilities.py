"""Facilities: the shop space - leases, rent, landlord."""

from ..models import AgentReport
from .spec import COMMON_TOOLS, AgentSpec

SPEC = AgentSpec(
    name="facilities",
    description="Handles the shop space: leases, rent amounts and due dates, and landlord "
                "communication drafts.",
    prompt_file="facilities.md",
    mcp_tools=COMMON_TOOLS | {
        "get_lease",
        "get_cash_balance",
        "list_payment_requests",
        "save_draft",
    },
    output_type=AgentReport,
)
