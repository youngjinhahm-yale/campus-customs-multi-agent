"""Customer Service: drafts messages for customers (never sends them)."""

from ..models import AgentReport
from .spec import COMMON_TOOLS, AgentSpec

SPEC = AgentSpec(
    name="customer_service",
    description="Drafts clear, accurate messages to customers and saves them on the board; "
                "never sends anything.",
    prompt_file="customer_service.md",
    mcp_tools=COMMON_TOOLS | {
        "check_stock",
        "list_inventory",
        "get_pricing",
        "save_draft",
        "list_drafts",
    },
    output_type=AgentReport,
)
