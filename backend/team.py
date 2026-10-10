"""The Campus Customs agent team: five PydanticAI agents with full connectivity.

* Every agent gets the same `delegate_to_agent` tool, so any agent can hand a task
  to any other agent.
* Every agent gets only its allowlisted tools from the one MCP connection.
* Every agent loop is driven with `Agent.iter`, and each step is appended to
  output/audit_trail.json.
* One ticket shares one usage counter and one delegation budget across all agents.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models import Model
from pydantic_ai.usage import RunUsage

from . import audit
from .agents import SPECS
from .agents.spec import AgentSpec
from .config import (
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_TICKET,
    MODEL_NAME,
    PROMPTS_DIR,
    TICKET_USAGE_LIMITS,
    WORKING_DB,
    build_model,
)
from .mcp_tools import build_mcp_toolset, tools_for
from .models import AGENT_NAMES, AgentName, DelegationBudget, TeamDeps, TicketResolution


class Team:
    """Holds the MCP connection and the five agents. Use as `async with Team() as team:`."""

    def __init__(self, model: Model | None = None, db_path=WORKING_DB) -> None:
        self.model = model or build_model()
        self.mcp = build_mcp_toolset(db_path)
        self.agents: dict[str, Agent[TeamDeps, Any]] = {
            name: self._build_agent(spec) for name, spec in SPECS.items()
        }

    async def __aenter__(self) -> "Team":
        await self.mcp.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.mcp.__aexit__(*exc)

    async def call_tool(self, name: str, **args: Any) -> Any:
        """Call an MCP tool directly (for the backend/human side, not for agents)."""
        result = await self.mcp.client.call_tool(name, args)
        data = result.structured_content
        # FastMCP wraps non-object returns (e.g. lists) as {"result": ...}.
        if isinstance(data, dict) and set(data) == {"result"}:
            return data["result"]
        return data

    # -- building -----------------------------------------------------------------

    def _build_agent(self, spec: AgentSpec) -> Agent[TeamDeps, Any]:
        agent = Agent(
            self.model,
            name=spec.name,
            deps_type=TeamDeps,
            output_type=spec.output_type,
            toolsets=[tools_for(self.mcp, spec.mcp_tools)],
            tools=[Tool(self._delegate_tool, name="delegate_to_agent", takes_ctx=True)],
            retries=2,
        )
        prompt_path = PROMPTS_DIR / spec.prompt_file

        @agent.instructions
        def instructions(ctx: RunContext[TeamDeps]) -> str:
            # Re-read each run so prompt edits apply without a restart.
            return prompt_path.read_text(encoding="utf-8") + "\n\n" + _runtime_context(ctx.deps)

        return agent

    async def _delegate_tool(self, ctx: RunContext[TeamDeps], agent: AgentName, task: str) -> str:
        """Hand a specific task to another teammate and get their report back.

        agent: one of boss, inventory, accounting, facilities, customer_service (not yourself).
        task: a self-contained request - include the ticket id, what you already know
              (with numbers from tools), and exactly what you need back.
        """
        deps = ctx.deps
        refusal = None
        if agent == deps.agent:
            refusal = "You cannot delegate to yourself; do the work with your own tools."
        elif agent not in AGENT_NAMES:
            refusal = f"Unknown agent {agent!r}. Choose one of {list(AGENT_NAMES)}."
        elif deps.depth >= MAX_DELEGATION_DEPTH:
            refusal = (f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached. Finish with "
                       "what you have and report any gaps as blockers.")
        elif deps.budget.used >= deps.budget.max_delegations:
            refusal = (f"This ticket has used all {deps.budget.max_delegations} delegations. "
                       "Finish with what you have.")
        if refusal:
            audit.record(deps, "delegation_refused", {"to": agent, "task": task, "reason": refusal})
            return refusal

        deps.budget.used += 1
        sub_deps = TeamDeps(
            ticket_id=deps.ticket_id,
            run_id=deps.run_id,
            budget=deps.budget,
            agent=agent,
            depth=deps.depth + 1,
            chain=[*deps.chain, agent],
        )
        audit.record(deps, "delegation_start", {"to": agent, "task": task})
        output = await self.run_agent(agent, task, sub_deps, usage=ctx.usage)
        audit.record(deps, "delegation_end", {"to": agent, "output": output.model_dump()})
        return output.model_dump_json()

    # -- running ------------------------------------------------------------------

    async def run_agent(self, name: AgentName, prompt: str, deps: TeamDeps,
                        usage: RunUsage | None = None) -> Any:
        """Drive one agent loop step by step, auditing every node."""
        agent = self.agents[name]
        step = 0
        async with agent.iter(prompt, deps=deps, usage=usage,
                              usage_limits=TICKET_USAGE_LIMITS) as run:
            async for node in run:
                step += 1
                audit.record_node(deps, step, node, run.usage)
        return run.result.output

    async def run_ticket(self, ticket_id: int) -> TicketResolution | None:
        """The Boss works one ticket, delegating as needed. Returns the final call."""
        deps = TeamDeps(
            ticket_id=ticket_id,
            run_id=f"t{ticket_id}-{uuid.uuid4().hex[:8]}",
            budget=DelegationBudget(max_delegations=MAX_DELEGATIONS_PER_TICKET),
        )
        audit.record(deps, "run_start", {"ticket_id": ticket_id, "model": MODEL_NAME})
        prompt = (
            f"Work ticket {ticket_id}. Read it, involve the teammates it needs, make the "
            "final call, record it with update_ticket, and return your TicketResolution."
        )
        try:
            result = await self.run_agent("boss", prompt, deps)
        except UsageLimitExceeded as exc:
            audit.record(deps, "error", {"type": "usage_limit", "message": str(exc)})
            return None
        except Exception as exc:  # recorded, then re-raised for the caller
            audit.record(deps, "error", {"type": type(exc).__name__, "message": str(exc)})
            raise
        audit.record(deps, "run_end", {"resolution": result.model_dump(),
                                       "delegations_used": deps.budget.used})
        return result


def _runtime_context(deps: TeamDeps) -> str:
    teammates = "\n".join(
        f"- {name}: {spec.description}" for name, spec in SPECS.items() if name != deps.agent
    )
    can_delegate = deps.depth < MAX_DELEGATION_DEPTH
    return (
        "## Run context\n"
        f"- You are: **{deps.agent}**. Use '{deps.agent}' for every requested_by / author / "
        "updated_by argument.\n"
        f"- Ticket: {deps.ticket_id}\n"
        f"- Delegation chain so far: {' -> '.join(deps.chain)}\n"
        f"- Delegation depth: {deps.depth} of {MAX_DELEGATION_DEPTH} "
        f"({'you may delegate' if can_delegate else 'you may NOT delegate further'})\n"
        f"- Team delegations used on this ticket: {deps.budget.used} of {deps.budget.max_delegations}\n"
        f"- Model: {MODEL_NAME}\n\n"
        f"## Teammates (call delegate_to_agent)\n{teammates}"
    )
