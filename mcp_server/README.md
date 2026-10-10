# Campus Customs MCP Server

A [FastMCP](https://gofastmcp.com) server that gives the Campus Customs agent team (Boss, Inventory, Accounting, Facilities, Customer Service) one shared set of shop tools. The agents never touch the database directly. Every shop fact and every write goes through these tools, and every tool returns only what is stored in the database. Nothing is invented.

## Database

- `data/campus_customs_new.db` is the **working copy** the server reads and writes (override with the `CAMPUS_DB_PATH` env var, e.g., for tests).
- `data/campus_customs.db` is the original and is never modified. To reset, copy it over the working file (`python -m backend.reset_db`).
- "Today" for the shop is `desk.date_today`, not the system clock.
- The server adds two tables to the working copy on first use: `payment_requests` (payments and POs waiting for a human) and `drafts` (messages that are never sent).

## Tools

| Tool | Tables | What it does |
|---|---|---|
| `get_shop_date()` | desk | Shop "today" and desk notes |
| `list_tickets()` | tickets | Every ticket, resolved or not |
| `list_open_tickets()` | tickets | All tickets not yet resolved |
| `get_ticket(ticket_id)` | tickets | One ticket with all fields |
| `update_ticket(ticket_id, status, note, updated_by)` | tickets | Set status and append a dated note |
| `check_stock(sku, size, qty_needed)` | inventory | On-hand qty and shortfall for one SKU and size |
| `list_inventory(sku?)` | inventory | Every size for a SKU (or all stock) |
| `get_pricing(sku)` | pricing | Unit cost and list price |
| `check_margin(sku, unit_price, qty)` | pricing | Discount %, profit, margin %, below-cost flag |
| `list_vendors()` | vendors | Vendors, specialties, lead days |
| `check_vendor_status(vendor_id)` | vendors, invoices, desk | Lead time, open/overdue invoices, `will_ship` |
| `get_cash_balance(account?)` | cash_accounts, payment_requests | Balance, pending total, projected balance |
| `get_invoice(invoice_id)` | invoices, vendors, desk | One invoice, overdue status |
| `list_open_invoices()` | invoices, vendors, desk | All unpaid invoices |
| `get_lease(lease_id)` | leases, desk | Rent, landlord, due date, days until due |
| `request_invoice_payment(...)` | invoices, cash_accounts → payment_requests | Pending request to pay an invoice |
| `request_rent_payment(...)` | leases, cash_accounts → payment_requests | Pending request to pay rent |
| `request_purchase_order(...)` | vendors, invoices, pricing, inventory, cash_accounts → payment_requests | Pending restock PO (qty × unit_cost) |
| `list_payment_requests(status?, ticket_id?)` | payment_requests | Requests and their status |
| `approve_payment_request(request_id, approved_by)` | payment_requests, cash_accounts, payments, invoices, leases | **HUMAN ONLY.** Pays it, refusing if cash would go negative |
| `reject_payment_request(request_id, decided_by, reason)` | payment_requests | **HUMAN ONLY.** Rejects it |
| `save_draft(...)` | drafts | Save a message draft (never sent) |
| `list_drafts(ticket_id?)` | drafts | Saved drafts |

**Money rules enforced in the server:** agents can only create *pending* requests. Amounts are always looked up from the database. A payment that would make the balance negative is refused. A purchase order can't be approved while its vendor has an open invoice. Duplicate pending requests are refused. The backend never gives the two HUMAN ONLY tools to an agent.

## Run

```bash
pip install -r requirements.txt
python mcp_server/server.py
```
