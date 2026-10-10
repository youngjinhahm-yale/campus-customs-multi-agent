"""FastAPI backend for the Campus Customs dashboard.

Start it from the backend/ folder:

    uvicorn main:app --reload --port 8000

Every shop fact and every database change goes through the MCP server (via the
Team's MCP connection). The only files this module touches directly are the audit
trail it reads for /api/events and the database copy made by /api/reset.
"""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# `uvicorn main:app` runs this file as a top-level module from backend/, so make the
# hw5 folder importable and load the rest of the package as `backend.*`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend import audit  # noqa: E402
from backend.config import AUDIT_PATH, MODEL_NAME  # noqa: E402
from backend.reset_db import reset_database  # noqa: E402
from backend.team import Team  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with Team() as team:
        app.state.team = team
        app.state.runs = {}                # ticket_id -> run status dict
        app.state.run_lock = asyncio.Lock()  # one ticket at a time (shared cash)
        yield


app = FastAPI(title="Campus Customs Multi-Agent Operations", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def team() -> Team:
    return app.state.team


async def mcp(tool: str, **args: Any) -> Any:
    return await team().call_tool(tool, **args)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human approving")


class RejectBody(BaseModel):
    decided_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)


# --- Tickets -------------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "model": MODEL_NAME}


@app.get("/api/tickets")
async def list_tickets() -> list[dict]:
    """Every ticket, with a simple open/resolved state plus the detailed status."""
    tickets = await mcp("list_tickets")
    for t in tickets:
        t["state"] = "resolved" if t["status"] == "resolved" else "open"
        t["run"] = app.state.runs.get(t["id"])
    return tickets


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: int) -> dict:
    ticket = await mcp("get_ticket", ticket_id=ticket_id)
    if not ticket.get("found"):
        raise HTTPException(404, f"No ticket {ticket_id}")
    ticket["state"] = "resolved" if ticket["status"] == "resolved" else "open"
    ticket["run"] = app.state.runs.get(ticket_id)
    return ticket


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int, wait: bool = False) -> dict:
    """Run the agent team on one ticket.

    By default the run happens in the background so the board can poll /api/events
    and watch the agents work; pass ?wait=true to block until the Boss decides.
    """
    ticket = await mcp("get_ticket", ticket_id=ticket_id)
    if not ticket.get("found"):
        raise HTTPException(404, f"No ticket {ticket_id}")
    if app.state.run_lock.locked():
        raise HTTPException(409, "Another ticket is running; tickets run one at a time.")

    status = {"ticket_id": ticket_id, "status": "running", "started_at": now(),
              "finished_at": None, "resolution": None, "error": None}
    app.state.runs[ticket_id] = status

    async def work() -> None:
        async with app.state.run_lock:
            try:
                resolution = await team().run_ticket(ticket_id)
                if resolution is None:
                    status.update(status="stopped", error="Usage limit reached")
                else:
                    # The team's work on this ticket is finished, so the board marks it
                    # resolved. The Boss's own outcome (e.g. waiting_approval) is kept in
                    # the note; pending payments stay in the approval panel until a human acts.
                    await mcp("update_ticket", ticket_id=ticket_id, status="resolved",
                              note=f"Agent run finished. Boss outcome: {resolution.final_status}.",
                              updated_by="dashboard")
                    status.update(status="done", resolution=resolution.model_dump(),
                                  boss_outcome=resolution.final_status)
            except Exception as exc:  # also recorded in the audit trail by Team
                status.update(status="error", error=f"{type(exc).__name__}: {exc}")
            status["finished_at"] = now()

    if wait:
        await work()
        return status
    asyncio.create_task(work())
    return status


@app.get("/api/tickets/{ticket_id}/run")
async def run_status(ticket_id: int) -> dict:
    status = app.state.runs.get(ticket_id)
    if status is None:
        raise HTTPException(404, f"Ticket {ticket_id} has not been run since the server started")
    return status


# --- Agent events (from the audit trail) ---------------------------------------

def _summarize(event: dict) -> dict:
    """Reduce one audit event to what the board shows: who said what, which tools."""
    detail = event.get("detail", {})
    said, tool_calls, tool_results = None, [], []
    parts = detail.get("parts", [])
    if not isinstance(parts, list):
        # Older entries stored an over-long parts list as one clipped string.
        parts = [{"type": "text", "content": str(parts)}] if event["event"] == "model_response" else []
    parts = [p for p in parts if isinstance(p, dict)]
    if event["event"] == "model_response":
        texts = [p["content"] for p in parts if p.get("type") == "text"]
        said = "\n".join(texts) or None
        tool_calls = [{"tool": p["tool"], "args": p["args"]}
                      for p in parts if p.get("type") == "tool_call"]
    elif event["event"] == "model_request":
        tool_results = [{"tool": p.get("tool"), "content": p.get("content")}
                        for p in parts if p.get("type") in ("tool_return", "retry")]
    elif event["event"] == "final_output":
        said = json.dumps(detail.get("output"), default=str)
    elif event["event"] in ("delegation_start", "delegation_refused"):
        said = f"-> {detail.get('to')}: {detail.get('task')}"
        if detail.get("reason"):
            said += f" (refused: {detail['reason']})"
    elif event["event"] == "user_prompt":
        said = detail.get("prompt")
    return {
        "ts": event["ts"], "run_id": event["run_id"], "ticket_id": event["ticket_id"],
        "agent": event["agent"], "depth": event["depth"], "step": event["step"],
        "event": event["event"], "said": said, "tool_calls": tool_calls,
        "tool_results": tool_results, "usage": event.get("usage"), "detail": detail,
    }


@app.get("/api/events")
async def events(limit: int = Query(100, ge=1, le=1000),
                 after: int = Query(0, ge=0, description="return events with index >= after"),
                 ticket_id: int | None = None) -> dict:
    """Recent agent events, newest last. Poll with ?after=<next_after> to get only new ones."""
    all_events = []
    if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size:
        all_events = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    indexed = [(i, e) for i, e in enumerate(all_events) if i >= after
               and (ticket_id is None or e.get("ticket_id") == ticket_id)]
    indexed = indexed[-limit:]
    return {
        "total": len(all_events),
        "next_after": len(all_events),
        "events": [{"index": i, **_summarize(e)} for i, e in indexed],
    }


# --- Payments (human approval) ----------------------------------------------------

@app.get("/api/payment-requests")
async def payment_requests(status: str | None = None, ticket_id: int | None = None) -> list[dict]:
    """Payments and purchase orders the agents prepared, for the approval panel."""
    args: dict[str, Any] = {}
    if status:
        args["status"] = status
    if ticket_id is not None:
        args["ticket_id"] = ticket_id
    return await mcp("list_payment_requests", **args)


@app.post("/api/payment-requests/{request_id}/approve")
async def approve(request_id: int, body: ApproveBody) -> dict:
    """A human clicked Approve. This is the only path that moves cash.

    The MCP tool refuses if the balance would go negative or the vendor is still
    blocked; on success it writes payments, cash_accounts, and invoices/leases.
    """
    result = await mcp("approve_payment_request", request_id=request_id,
                       approved_by=body.approved_by)
    audit.record(None, "human_approval",
                 {"request_id": request_id, "approved_by": body.approved_by, "result": result})
    if not result.get("paid"):
        not_found = "No payment request" in result.get("message", "")
        raise HTTPException(404 if not_found else 409, detail=result)
    return result


@app.post("/api/payment-requests/{request_id}/reject")
async def reject(request_id: int, body: RejectBody) -> dict:
    result = await mcp("reject_payment_request", request_id=request_id,
                       decided_by=body.decided_by, reason=body.reason)
    audit.record(None, "human_rejection",
                 {"request_id": request_id, "decided_by": body.decided_by,
                  "reason": body.reason, "result": result})
    if not result.get("rejected"):
        raise HTTPException(409, detail=result)
    return result


# --- Cash, drafts, reset -------------------------------------------------------

@app.get("/api/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts (plus what's pending against it)."""
    return await mcp("get_cash_balance", account="checking")


@app.get("/api/drafts")
async def drafts(ticket_id: int | None = None) -> list[dict]:
    """Messages the agents drafted. They stay on the board; nothing is sent."""
    return await mcp("list_drafts", **({"ticket_id": ticket_id} if ticket_id is not None else {}))


@app.post("/api/reset")
async def reset() -> dict:
    """Copy campus_customs.db over campus_customs_new.db for a fresh run.

    The audit trail is append-only and is not wiped.
    """
    if app.state.run_lock.locked():
        raise HTTPException(409, "A ticket is running; reset after it finishes.")
    reset_database()
    app.state.runs.clear()
    audit.record(None, "db_reset", {"message": "Working database reset to the original."})
    return {"reset": True, "cash": await mcp("get_cash_balance", account="checking"),
            "tickets": [{"id": t["id"], "status": t["status"]} for t in await mcp("list_tickets")]}
