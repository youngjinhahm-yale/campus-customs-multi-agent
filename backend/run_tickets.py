"""Run the agent team over open tickets from the command line.

    python -m backend.run_tickets --reset          # full run: reset DB, then every open ticket
    python -m backend.run_tickets --ticket 102     # one ticket against the current working DB

Tickets run one at a time, so later tickets see the payment requests earlier ones filed
and the Boss can prioritize cash across them.
"""

from __future__ import annotations

import argparse
import asyncio

from .reset_db import reset_database
from .team import Team


async def main(ticket: int | None, reset: bool) -> None:
    if reset:
        reset_database()
        print("Working database reset to the original.")
    async with Team() as team:
        # Ticket list comes from the MCP server, like every other shop fact.
        ids = [ticket] if ticket is not None else [
            t["id"] for t in await team.call_tool("list_open_tickets")]
        for ticket_id in ids:
            print(f"\n=== Ticket {ticket_id} ===")
            resolution = await team.run_ticket(ticket_id)
            print(resolution.model_dump_json(indent=2) if resolution
                  else "Stopped: usage limit reached (see output/audit_trail.json).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticket", type=int, help="run a single ticket id")
    parser.add_argument("--reset", action="store_true", help="reset the working DB first")
    args = parser.parse_args()
    asyncio.run(main(args.ticket, args.reset))
