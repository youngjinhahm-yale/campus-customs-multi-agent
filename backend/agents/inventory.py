"""Inventory: stock by SKU and size, shortfalls, and which vendor can restock."""

from ..models import AgentReport
from .spec import COMMON_TOOLS, AgentSpec

SPEC = AgentSpec(
    name="inventory",
    description="Checks stock by SKU and size, finds shortfalls, and works out which vendor "
                "can restock and how long it takes.",
    prompt_file="inventory.md",
    mcp_tools=COMMON_TOOLS | {
        "check_stock",
        "list_inventory",
        "list_vendors",
        "check_vendor_status",
        "get_pricing",
    },
    output_type=AgentReport,
)
