"""Accounting: cash, invoices, margins, and payment / purchase-order requests for a human."""

from ..models import AgentReport
from .spec import COMMON_TOOLS, AgentSpec

SPEC = AgentSpec(
    name="accounting",
    description="Watches cash and invoices, checks margins on discounts, and prepares payments "
                "or purchase orders for human approval (never pays anything itself).",
    prompt_file="accounting.md",
    mcp_tools=COMMON_TOOLS | {
        "get_cash_balance",
        "get_invoice",
        "list_open_invoices",
        "list_vendors",
        "check_vendor_status",
        "get_pricing",
        "check_margin",
        "get_lease",
        "request_invoice_payment",
        "request_rent_payment",
        "request_purchase_order",
        "list_payment_requests",
    },
    output_type=AgentReport,
)
