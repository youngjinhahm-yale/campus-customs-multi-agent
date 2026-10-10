# Campus Customs Multi-Agent Operations (HW5)

An agent team that runs a campus shop. Five PydanticAI agents (**Boss, Inventory, Accounting, Facilities, Customer Service**) work tickets through a **FastMCP server** over a SQLite database. A **FastAPI backend** runs the team, and a **React dashboard** lets a human watch the agents and approve payments. Every agent uses only `gpt-6-luna` through Portkey.

```
data/campus_customs.db       original shop database (never modified)
data/campus_customs_new.db   working copy the MCP server and backend read/write
mcp_server/                  FastMCP server: every shop tool (see mcp_server/README.md)
backend/                     agents, prompts, models, FastAPI routes (main.py)
frontend/                    React + Vite + TypeScript dashboard
output/                      harness, smoke test, plans/results, audit trail
```

## 1. One-time setup

Requires Python 3.12+ and Node 20+.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # macOS/Linux: .venv/bin/pip
cd frontend && npm install && cd ..
cp .env.example .env                               # then put your real PORTKEY_API_KEY in .env
```

`.env` is git-ignored. Never commit a real key.

## 2. Get a clean database (copy original → working copy)

Whenever you need a clean run, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
# or:  python -m backend.reset_db
```

## 3. Start the MCP server

```bash
python mcp_server/server.py
```

It talks to `data/campus_customs_new.db`. You normally don't need to start it by hand: the backend launches it over stdio, and Claude Code launches it from `.mcp.json`. `.mcp.json` points at `.venv/Scripts/python.exe` (Windows). On macOS/Linux, change it to `.venv/bin/python`.

## 4. Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The backend runs at http://localhost:8000. Routes are listed in `output/harness.md` §8. It allows the dashboard origin http://localhost:5173.

## 5. Start the React board

```bash
cd frontend
npm run dev
```

This opens http://localhost:5173. Pick a ticket, press **Start the team**, watch the agents on **The Floor**, then type your name under **Needs your signature** and approve payments. The **Till** shows checking drop after each approved payment.

## 6. Full three-ticket run

1. **Reset the DB first:** click **↺ Reset shop** on the board, or run `python -m backend.reset_db` (or `curl -X POST http://localhost:8000/api/reset`). Checking starts at **$3,400.00**.
2. Run tickets **101 → 102 → 103** in order. They share one checking account.
3. Approve the payment requests the agents prepare (agents can never pay on their own).

Command-line alternative (no dashboard): `python -m backend.run_tickets --reset`.

## Results and docs

- `output/harness.md`: tables, MCP tools, agents, routes, dashboard, safety rules
- `output/desk_tickets.html`: Expected vs. Actual per ticket, the Cash itemization, and the Reflection
- `output/resolved_tickets.json`, `output/resolved_board.html`: results of the graded run ($3,400 → $160)
- `output/audit_trail.json`: append-only log of every agent-loop step, approval and reset
- `output/design.md`: dashboard design choices
- `AI_prompts.md`: prompts typed to the vibe coder
