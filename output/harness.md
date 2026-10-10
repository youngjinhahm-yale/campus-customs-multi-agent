# Harness — Campus Customs Multi-Agent Operations

Working database: `data/campus_customs_new.db` (copy of `data/campus_customs.db`; the original stays untouched for resets).

---

## 1. Database tables

### `desk`
| Field | Type |
|---|---|
| date_today | TEXT |
| notes | TEXT |

**Why it matters:** `date_today` (2026-08-31) is "today" for the shop — every agent uses it to decide what is overdue or due soon.

### `tickets`
| Field | Type |
|---|---|
| id | INTEGER PK |
| type | TEXT (`customer_order`, `rent_notice`, `price_override`) |
| requester | TEXT |
| subject | TEXT |
| sku | TEXT |
| size | TEXT |
| qty | INTEGER |
| lease_id | INTEGER → leases.id |
| invoice_id | INTEGER → invoices.id |
| status | TEXT |
| notes | TEXT |
| created_at | TEXT |

**Why it matters:** The board of work — Boss reads each ticket and routes it; the `sku`/`lease_id`/`invoice_id` links tell it which specialist to involve.

### `inventory`
| Field | Type |
|---|---|
| sku | TEXT (PK with size) |
| name | TEXT |
| size | TEXT |
| qty | INTEGER |
| location | TEXT |

**Why it matters:** Inventory agent checks stock by SKU + size here to spot shortfalls.

### `pricing`
| Field | Type |
|---|---|
| sku | TEXT PK |
| unit_cost | REAL |
| list_price | REAL |

**Why it matters:** Accounting uses cost vs. list price to check margins on discounts and to cost out purchase orders.

### `vendors`
| Field | Type |
|---|---|
| id | INTEGER PK |
| name | TEXT |
| specialty | TEXT |
| lead_days | INTEGER |

**Why it matters:** Inventory picks the right vendor by specialty; `lead_days` is the only valid source for restock timing.

### `leases`
| Field | Type |
|---|---|
| id | INTEGER PK |
| space_name | TEXT |
| landlord | TEXT |
| monthly_rent | REAL |
| next_due | TEXT |
| notes | TEXT |

**Why it matters:** Facilities uses this for rent amount and due date.

### `cash_accounts`
| Field | Type |
|---|---|
| name | TEXT PK |
| balance | REAL |
| date | TEXT |

**Why it matters:** The only money the shop has (no revenue is modeled) — the pay tool must refuse anything that would make a balance negative.

### `payments`
| Field | Type |
|---|---|
| id | INTEGER PK |
| kind | TEXT |
| ref_id | INTEGER |
| amount | REAL |
| account | TEXT |
| paid_at | TEXT |
| approved_by | TEXT |

**Why it matters:** The record of every human-approved payment; `approved_by` proves a human signed off. Empty at start.

### `invoices`
| Field | Type |
|---|---|
| id | INTEGER PK |
| vendor_id | INTEGER → vendors.id |
| amount | REAL |
| due_date | TEXT |
| status | TEXT |
| description | TEXT |

**Why it matters:** Accounting tracks what is owed; an open invoice blocks that vendor from shipping new product.

---

## 2. Starting data snapshot (as of 2026-08-31)

- **Cash:** checking = **$3,400.00**
- **Vendors:** 1 Bulldog Print Co (apparel reprint, 5 days) · 2 Elm City Gifts (mugs/small goods, 3 days) · 3 QuickShip CT (local courier, 1 day)
- **Open invoice:** #501 — Bulldog Print Co, $840.00, due 2026-08-28 (**overdue**), "Rush reprint CC-TEE-WHITE S"
- **Lease:** #1 Chapel Street shop, Elm City Properties, $2,400/month, next due 2026-09-02
- **Stock highlights:** CC-TEE-WHITE S = 0 · CC-HOOD-NAVY M = 8 (S 4, L 14, XL 6) · CC-MUG-CREST OS = 0 · CC-HAT-BLUE OS = 40
- **Pricing:** Hoodie $22 cost / $58 list · Tee $8 / $28 · Cap $6 / $22 · Mug $3.50 / $14

---

## 3. The three open tickets and how they link

### Ticket 101 — `customer_order` (Tauhid Zaman): 1 × Bulldog tee, size S
- `sku`/`size` → **inventory**: CC-TEE-WHITE S has **qty 0** → shortfall of 1.
- `invoice_id` 501 → **invoices** → `vendor_id` 1 → **vendors**: Bulldog Print Co (apparel).
- Invoice 501 is **open and overdue** ($840, due 08-28), so Bulldog Print **will not ship** until it is paid.
- `pricing`: tee cost $8, list $28.
- **Agents involved:** Boss → Inventory (shortfall + vendor) → Accounting (pay #501 with human approval, then restock PO) → Customer Service (draft delay message; 5-day lead time after payment).

### Ticket 102 — `rent_notice` (Elm City Properties): rent due in 2 days
- `lease_id` 1 → **leases**: $2,400 due 2026-09-02 (2 days after today).
- **cash_accounts**: $3,400 available.
- **Agents involved:** Boss → Facilities (confirm lease/amount/date) → Accounting (prepare $2,400 rent payment for human approval).

### Ticket 103 — `price_override` (Yale AI Club): 20 hoodies, size M, bulk discount
- `sku`/`size` → **inventory**: CC-HOOD-NAVY M has **8** → shortfall of **12**.
- `pricing`: cost $22, list $58 → margin room for a discount (anything above $22/unit is still positive margin).
- Restock comes from Bulldog Print Co (apparel) — **same vendor blocked by invoice 501**.
- **Agents involved:** Boss → Inventory (shortfall + vendor) → Accounting (margin check on discount, PO cost) → Customer Service (draft quote/reply) → Boss final call.

### Cross-ticket tension (the cash squeeze)
| Step | Cash left |
|---|---|
| Start | $3,400 |
| Pay invoice #501 ($840) | $2,560 |
| Pay rent ($2,400) | $160 |
| Restock 12 hoodies M (12 × $22 = $264) | **−$104 → refused** |

Rent and the overdue invoice together nearly drain the account, so the Boss must prioritize (rent is a hard obligation; #501 unblocks the vendor for both 101 and 103), and the pay tool must refuse anything that would go negative.

---

## 4. MCP tools (`mcp_server/server.py`)

All tools read `data/campus_customs_new.db` and return only database values.

### `check_stock(sku, size, qty_needed)`
- **Reads:** `inventory`
- **Unlocks:** Ticket **103** (also used for 101)
- **Why:** Ticket 103 asks for 20 CC-HOOD-NAVY in size M. This tool returns the 8 on hand and a shortfall of 12, so Inventory knows a restock is needed before Accounting can quote the bulk discount.

### `check_vendor_status(vendor_id)`
- **Reads:** `vendors`, `invoices` (plus `desk.date_today`)
- **Unlocks:** Ticket **101**
- **Why:** Ticket 101's tee (CC-TEE-WHITE S, qty 0) links to invoice 501. This tool shows that vendor 1, Bulldog Print Co, has $840 open and overdue (due 08-28 vs. today 08-31), so `will_ship` is false and the 5-day lead time can't start until a human approves paying #501.

### `get_lease(lease_id)`
- **Reads:** `leases` (plus `desk.date_today`)
- **Unlocks:** Ticket **102**
- **Why:** Ticket 102 is the rent notice for lease 1. This tool confirms $2,400 is owed to Elm City Properties on 2026-09-02 (2 days from today) from the database itself, not the email text, so Facilities can hand Accounting a verified amount and deadline.

---

## 5. Agent team (`backend/`)

Built with PydanticAI. Every agent uses **only `gpt-6-luna` through Portkey** (`backend/config.py`, constant `MODEL_NAME`, not overridable). Every request asks for `gpt-6-luna`. Portkey labels its responses with its deployment name, `gpt-6-luna-global`, which appears as `model_name` in `model_response` audit events. That is the same model, not a different one. Each audit event's top-level `model` field records the requested `gpt-6-luna`. Prompts live in `backend/prompts/` (one file per agent), data types in `backend/models.py`, role definitions in `backend/agents/`, and the agent loop and delegation in `backend/team.py`.

**Full connectivity:** every agent has the same `delegate_to_agent(agent, task)` tool, so any agent can hand work to any other agent. The sub-agent runs its own loop and returns its structured report. Guards: no self-delegation, max depth 2, max 8 delegations per ticket, and one shared token/request budget per ticket.

| Agent | Prompt | Output type | MCP tools it can call |
|---|---|---|---|
| **Boss** | `prompts/boss.md` | `TicketResolution` | get_ticket, get_shop_date, list_open_tickets, update_ticket, list_payment_requests, list_drafts, get_cash_balance |
| **Inventory** | `prompts/inventory.md` | `AgentReport` | get_ticket, get_shop_date, check_stock, list_inventory, list_vendors, check_vendor_status, get_pricing |
| **Accounting** | `prompts/accounting.md` | `AgentReport` | get_ticket, get_shop_date, get_cash_balance, get_invoice, list_open_invoices, list_vendors, check_vendor_status, get_pricing, check_margin, get_lease, request_invoice_payment, request_rent_payment, request_purchase_order, list_payment_requests |
| **Facilities** | `prompts/facilities.md` | `AgentReport` | get_ticket, get_shop_date, get_lease, get_cash_balance, list_payment_requests, save_draft |
| **Customer Service** | `prompts/customer_service.md` | `AgentReport` | get_ticket, get_shop_date, check_stock, list_inventory, get_pricing, save_draft, list_drafts |

All agents also have `delegate_to_agent`. No agent has `approve_payment_request` or `reject_payment_request`; `backend/mcp_tools.py` raises an error if one is ever allowlisted.

**Audit trail:** `backend/team.py` drives every agent loop with `Agent.iter`. `backend/audit.py` appends one event per loop step to `output/audit_trail.json`. Each event records the user prompt, the model request (tool returns), the model response (tool calls and args), and the final output, plus delegation start/end/refused, run start/end, and errors. Every event carries the timestamp, run id, ticket, agent, depth, delegation chain, step, model, and running token usage. The file is appended to (never wiped) and written atomically.

---

## 6. Full MCP tool list (`mcp_server/server.py`)

The backend reaches the database only through these tools, over one stdio MCP connection. There is no second shop-tools layer. Tools added in Problem 5 are marked ★.

| Tool | Tables | Reads / writes | Used by |
|---|---|---|---|
| ★ `get_shop_date` | desk | read | all |
| ★ `list_open_tickets` | tickets | read | Boss |
| ★ `list_tickets` (Problem 7) | tickets | read | Backend `/api/tickets` (no agent) |
| ★ `get_ticket` | tickets | read | all |
| ★ `update_ticket` | tickets | **write** (status, notes) | Boss |
| `check_stock` | inventory | read | Inventory, Customer Service |
| ★ `list_inventory` | inventory | read | Inventory, Customer Service |
| ★ `get_pricing` | pricing | read | Inventory, Accounting, Customer Service |
| ★ `check_margin` | pricing | read | Accounting |
| ★ `list_vendors` | vendors | read | Inventory, Accounting |
| `check_vendor_status` | vendors, invoices, desk | read | Inventory, Accounting |
| ★ `get_cash_balance` | cash_accounts, payment_requests | read | Boss, Accounting, Facilities |
| ★ `get_invoice` | invoices, vendors, desk | read | Accounting |
| ★ `list_open_invoices` | invoices, vendors, desk | read | Accounting |
| `get_lease` | leases, desk | read | Accounting, Facilities |
| ★ `request_invoice_payment` | invoices, cash_accounts → payment_requests | **write** (pending only) | Accounting |
| ★ `request_rent_payment` | leases, cash_accounts → payment_requests | **write** (pending only) | Accounting |
| ★ `request_purchase_order` | vendors, invoices, pricing, inventory, cash_accounts → payment_requests | **write** (pending only) | Accounting |
| ★ `list_payment_requests` | payment_requests | read | Boss, Accounting, Facilities |
| ★ `approve_payment_request` | payment_requests, cash_accounts, payments, invoices, leases | **write** (money moves) | **Human only** |
| ★ `reject_payment_request` | payment_requests | **write** | **Human only** |
| ★ `save_draft` | drafts | **write** | Facilities, Customer Service |
| ★ `list_drafts` | drafts | read | Boss, Customer Service |

`payment_requests` and `drafts` are new tables. The server creates them in the working copy on first use, so a reset (copying `campus_customs.db` over `campus_customs_new.db`) clears them.

---

## 7. Safety

### Guardrails for real customers and real money
- **Human approval in code, not just in prompts.** Agents can only create *pending* payment requests. Money moves only in `approve_payment_request`. That tool is never given to any agent, and it rejects an `approved_by` that is empty or an agent name. Each payment row records who approved it.
- **Amounts come from the database.** Payment tools look up the invoice amount, lease rent, or qty × unit_cost themselves, so an agent can't mistype or inflate an amount.
- **No negative balances.** The pay step re-checks the balance at approval time and refuses (status `refused`) if cash is short. Request tools also warn when pending requests already exceed cash.
- **Vendor block enforced.** A purchase order can't be approved while that vendor has an open invoice.
- **No duplicates.** A second pending request for the same invoice/lease/SKU-size is refused.
- **Atomic money updates.** Payment insert, cash decrease, and invoice/lease update commit together or not at all.
- **Nothing is sent.** There is no email/vendor/landlord tool. Messages are `drafts` rows for a human to review.
- **Least privilege.** Each agent sees only the MCP tools its job needs (e.g., Customer Service can't file payments; Inventory can't write anything).
- **No invented facts.** Prompts require every number to come from a tool result, and reports list each fact with its `source_tool` so a human can check it.
- **Audit everything.** Every model call, tool call, tool result, delegation and final decision is appended to `output/audit_trail.json`.
- **Resettable sandbox.** Agents work on `campus_customs_new.db`; the original is never touched.
- **What a real business would add:** spending limits per approval tier (e.g., a second approver above a set amount), authenticated human identities instead of a typed name, PII redaction in logs, rate limits, and a kill switch to pause all agents.

### Limits that keep token use in check
- One model only (`gpt-6-luna`), set in one place.
- Per-ticket budget shared by all agents (`TICKET_USAGE_LIMITS`): **40 model requests, 80 tool calls, 300k total tokens**. Exceeding it stops the run and logs a `usage_limit` error.
- Delegation caps: **depth ≤ 2**, **≤ 8 delegations per ticket**, no self-delegation. Refusals are logged.
- Small toolsets per agent mean shorter tool schemas in every request.
- Prompts tell agents to batch questions into one delegation, skip re-checking facts a teammate already sourced, and stop as soon as they can decide.
- Long tool results are truncated in the audit log (4,000 chars) to keep the file manageable.
- Portkey cache is bypassed for correctness (live shop data), so the budget caps above are the main cost control.

---

## 8. Backend routes (`backend/main.py`)

Start from `backend/`: `uvicorn main:app --reload --port 8000` → http://localhost:8000. CORS allows the Vite dashboard at http://localhost:5173 (Problem 8, `frontend/`, `npm run dev`). Every route reads or writes shop data through the MCP server; `/api/events` reads the audit trail and `/api/reset` copies the original DB file.

- `GET /api/tickets`: all tickets with `state` (open/resolved), the detailed status, and the latest run status.
- `GET /api/tickets/{id}`: one ticket.
- `POST /api/tickets/{id}/run`: runs the agent team on that ticket in the background (202). `?wait=true` blocks until the Boss decides. One ticket runs at a time (409 if busy). When the run finishes, the ticket is marked `resolved` through the `update_ticket` MCP tool. The Boss's own outcome (e.g., `waiting_approval`) is kept in the ticket note and run status, and pending payments stay in the approval panel.
- `GET /api/tickets/{id}/run`: status of that ticket's last run (running/done/stopped/error plus the Boss's resolution).
- `GET /api/events?limit=&after=&ticket_id=`: recent agent events from `output/audit_trail.json`, showing what each agent said and which tools it called or got back. Poll with `after=next_after` for only the new ones.
- `GET /api/payment-requests?status=&ticket_id=`: payments and POs the agents prepared, for the approval panel.
- `POST /api/payment-requests/{id}/approve` body `{"approved_by": "<human name>"}`: human approval. **The only route that changes cash.** It writes payments, cash_accounts, and invoices/leases, and refuses (409) if cash would go negative, the vendor is blocked, or the approver is an agent name.
- `POST /api/payment-requests/{id}/reject` body `{"decided_by", "reason"}`: a human rejects a request. Nothing is paid.
- `GET /api/cash`: current checking balance from cash_accounts, plus the pending total and projected balance.
- `GET /api/drafts?ticket_id=`: drafted messages on the board (never sent).
- `POST /api/reset`: copies `campus_customs.db` over `campus_customs_new.db` for a fresh run (409 while a ticket is running). The audit trail is not wiped.
- `GET /api/health`: health check and the model in use (`gpt-6-luna`).

Human approvals, rejections, and resets are also appended to the audit trail (`human_approval`, `human_rejection`, `db_reset`).

---

## 9. Dashboard (`frontend/`)

React + Vite + TypeScript "Back Office" desk. Start it with `npm run dev` in `frontend/` → http://localhost:5173. It calls the backend directly at `http://localhost:8000` (CORS allows the Vite origin). Full design rationale is in `output/design.md`.

- **The Board:** the three tickets as pinned index cards with status chips. **Start the team →** calls `POST /api/tickets/{id}/run`. A green **RESOLVED** stamp lands when the run finishes.
- **The Floor:** a roster of five agent desks with live status lights, plus a transcript (polls `GET /api/events`) of speech bubbles, tool-call receipts, tool-result gists, and Boss → specialist handoff cards. Delegated work is indented by depth.
- **Shift report:** the Boss's final call, "For you" next steps, one card per agent (summary, tools used, requests/drafts produced), who wasn't needed, and the run's token cost.
- **The Till:** checking balance from `GET /api/cash`. It counts down with a red "−$X" when a payment clears, and shows pending vs. projected.
- **Needs your signature:** pending payments/POs from `GET /api/payment-requests` as vouchers. **Approve & pay** (`POST …/approve`) is enabled only after a human types a name. Reject needs a reason. A ledger shows past decisions.
- **Outbox:** drafts from `GET /api/drafts`, stamped *DRAFT · NOT SENT*.
- **↺ Reset shop:** `POST /api/reset` (confirm dialog, disabled while a run is live). `?ticket=101` opens the desk on a ticket.

---

## 10. Full run results (Problem 9)

Reset at 2026-10-10T22:16:52Z, then 101 → 102 → 103 run from the board. All three are **resolved** on the board, and the Boss's own outcomes are 101 `waiting_approval`, 102 `waiting_approval`, 103 `in_progress`.

| Ticket | Delegations | Requests / drafts | Human approval | Tokens |
|---|---|---|---|---|
| 101 | boss→inventory, inventory→accounting, boss→accounting, accounting→inventory, boss→customer_service | request #1 ($840 invoice 501), draft #1 | #1 approved by Youngjin Hahm | 65,292 |
| 102 | boss→facilities, facilities→accounting | request #2 ($2,400 rent) | #2 approved by Youngjin Hahm | 35,676 |
| 103 | boss→inventory + boss→accounting (sent in parallel), accounting→inventory, boss→customer_service | draft #2 (no PO: $264 > $160) | none | 60,074 |

**Cash:** $3,400.00 → −$840.00 → −$2,400.00 → **$160.00**, which matches `cash_accounts.checking` and the two `payments` rows. Approvals were signed right after ticket 103 finished. Evidence: `output/desk_tickets.html` (Actual, Cash, Reflection tabs), `output/resolved_tickets.json`, `output/resolved_board.html`, `output/audit_trail.json` (events 255–424 for this run).

---

## 11. Safety rules (summary)

| Rule | Where it's enforced |
|---|---|
| Today is `desk.date_today`, never the system clock | MCP tools compute overdue/due-in from `desk`. All prompts say so. |
| Lead times only from `vendors` | `list_vendors` / `check_vendor_status`. Prompts forbid guessing dates. |
| Vendor with an open invoice won't ship | `check_vendor_status.will_ship`. `approve_payment_request` refuses a PO while the vendor has an open invoice. |
| Human approval for every payment | Agents only get `request_*` tools (pending rows). `approve_payment_request` / `reject_payment_request` are human-only, never allowlisted (`backend/mcp_tools.py` raises if they are), reachable only via `POST /api/payment-requests/{id}/approve`, and refuse agent names. The dashboard needs a typed name. |
| Payments update the right tables | One transaction: `payments` row, `cash_accounts.balance` down, invoice → `paid` or lease `next_due` +1 month, request → `approved`. |
| No negative balances | The pay step re-checks the balance at approval and marks the request `refused` if short. Request tools warn when pending exceeds cash. |
| Cash only goes out | No revenue tools exist. The till says so. |
| Amounts can't be typed by agents | Invoice amount, lease rent, and qty × unit_cost are looked up from the DB. |
| No duplicate requests | A second pending request for the same invoice/lease/SKU-size is refused. |
| Nothing is sent | No email/vendor/landlord tools. `drafts` rows only, and the dashboard stamps them NOT SENT. |
| No invented facts | Prompts require tool-sourced numbers. Reports list facts with `source_tool`. |
| Reset before a full run | `python -m backend.reset_db` or `POST /api/reset` copies the untouched `campus_customs.db`. |
| Only `gpt-6-luna` | One constant in `backend/config.py`. Portkey labels it `gpt-6-luna-global`. |
| Token limits | Per ticket: 40 requests, 80 tool calls, 300k tokens shared by all agents. Delegation depth ≤ 2, ≤ 8 per ticket, no self-delegation. One run at a time. |
| Everything audited | Every loop step, delegation, approval, rejection and reset is appended to `output/audit_trail.json` (append-only, atomic writes). |
