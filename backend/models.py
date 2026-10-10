"""Data types shared by the agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[AgentName, ...] = (
    "boss", "inventory", "accounting", "facilities", "customer_service",
)

TicketStatus = Literal["open", "in_progress", "waiting_approval", "resolved"]


# --- Run-time context passed to every agent -------------------------------------

@dataclass
class DelegationBudget:
    """Shared by every agent working one ticket, so the cap covers the whole team."""
    max_delegations: int
    used: int = 0


@dataclass
class TeamDeps:
    ticket_id: int
    run_id: str
    budget: DelegationBudget
    agent: AgentName = "boss"
    depth: int = 0
    chain: list[AgentName] = field(default_factory=lambda: ["boss"])


# --- Agent outputs ----------------------------------------------------------------

class Fact(BaseModel):
    """One fact an agent relied on, with the MCP tool it came from."""
    label: str = Field(description="What the fact is, e.g. 'CC-TEE-WHITE S on hand'")
    value: str = Field(description="The value exactly as the tool returned it")
    source_tool: str = Field(description="MCP tool that returned it")


class AgentReport(BaseModel):
    """What a specialist (Inventory, Accounting, Facilities, Customer Service) hands back."""
    agent: AgentName
    ticket_id: int
    summary: str = Field(description="2-4 sentences: what you found and did")
    facts: list[Fact] = Field(default_factory=list)
    actions_taken: list[str] = Field(
        default_factory=list, description="Writes you made: requests filed, drafts saved")
    payment_request_ids: list[int] = Field(default_factory=list)
    draft_ids: list[int] = Field(default_factory=list)
    blockers: list[str] = Field(
        default_factory=list, description="Anything stopping the ticket, e.g. vendor blocked")
    recommendation: str = Field(description="What you advise the Boss to do next")


class TicketResolution(BaseModel):
    """The Boss's final call on one ticket."""
    ticket_id: int
    final_status: TicketStatus
    decision: str = Field(description="The final call in plain words")
    agents_consulted: list[AgentName] = Field(default_factory=list)
    payment_request_ids: list[int] = Field(
        default_factory=list, description="Requests waiting on a human")
    draft_ids: list[int] = Field(default_factory=list)
    next_steps_for_human: list[str] = Field(default_factory=list)
    summary: str


# --- Audit trail ------------------------------------------------------------------

AuditEventType = Literal[
    "run_start", "user_prompt", "model_request", "model_response", "final_output",
    "delegation_start", "delegation_end", "delegation_refused", "error", "run_end",
    "human_approval", "human_rejection", "db_reset",
]


class AuditEvent(BaseModel):
    """One line of output/audit_trail.json - one agent-loop step or team event."""
    ts: str
    run_id: str
    ticket_id: int | None
    agent: AgentName | None
    depth: int
    chain: list[str]
    step: int | None
    event: AuditEventType
    model: str
    detail: dict[str, Any]
    usage: dict[str, Any] | None = None
