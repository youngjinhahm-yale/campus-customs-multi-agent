"""Campus Customs MCP server.

Exposes shop tools over MCP for the multi-agent team. Every tool reads from (and,
for write tools, updates) the working copy data/campus_customs_new.db and returns
only what is in the database.

Money rules enforced here, not in the prompts:
  * Agents can only *request* payments. Nothing is paid until a human calls
    approve_payment_request (HUMAN ONLY - the backend never gives it to agents).
  * A payment that would make a cash balance negative is refused.
  * A purchase order is refused while the vendor still has an open invoice.
  * Amounts are always taken from the database (invoice amount, lease rent,
    qty x pricing.unit_cost), never from the caller.
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"
DB_PATH = Path(os.getenv("CAMPUS_DB_PATH", DEFAULT_DB))

mcp = FastMCP("campus-customs")

# Tables the original database does not have. They are created in the working copy
# on first use, so resetting (copying campus_customs.db over the working file) clears them.
EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL CHECK (kind IN ('invoice', 'rent', 'purchase_order')),
    ref_id INTEGER,
    vendor_id INTEGER,
    sku TEXT,
    size TEXT,
    qty INTEGER,
    amount REAL NOT NULL,
    account TEXT NOT NULL,
    reason TEXT,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'refused')),
    created_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    payment_id INTEGER
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(EXTRA_SCHEMA)
        yield conn
    finally:
        conn.close()


def _date_today(conn: sqlite3.Connection) -> str:
    """The shop's 'today' comes from desk.date_today, never the system clock."""
    return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]


def _rows(cursor) -> list[dict]:
    return [dict(r) for r in cursor.fetchall()]


def _open_invoices(conn: sqlite3.Connection, vendor_id: int, today: str) -> list[dict]:
    invoices = _rows(conn.execute(
        "SELECT id, amount, due_date, status, description FROM invoices "
        "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
        (vendor_id,),
    ))
    return [{**inv, "overdue": inv["due_date"] < today} for inv in invoices]


def _cash(conn: sqlite3.Connection, account: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)
    ).fetchone()


def _pending_total(conn: sqlite3.Connection, account: str) -> float:
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS t FROM payment_requests "
        "WHERE status = 'pending' AND account = ?",
        (account,),
    ).fetchone()["t"]


def _create_request(conn, *, ticket_id, kind, ref_id, vendor_id, sku, size, qty,
                    amount, account, reason, requested_by) -> dict:
    """Insert a pending payment request after duplicate and cash-projection checks."""
    dup = conn.execute(
        "SELECT id FROM payment_requests WHERE status = 'pending' AND kind = ? "
        "AND COALESCE(ref_id, -1) = COALESCE(?, -1) AND COALESCE(sku, '') = COALESCE(?, '') "
        "AND COALESCE(size, '') = COALESCE(?, '')",
        (kind, ref_id, sku, size),
    ).fetchone()
    if dup:
        return {"created": False, "existing_request_id": dup["id"],
                "message": "A pending request for this already exists; do not file a duplicate."}
    cash = _cash(conn, account)
    if cash is None:
        return {"created": False, "message": f"No cash account named {account!r}."}
    today = _date_today(conn)
    cur = conn.execute(
        "INSERT INTO payment_requests (ticket_id, kind, ref_id, vendor_id, sku, size, qty, "
        "amount, account, reason, requested_by, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
        (ticket_id, kind, ref_id, vendor_id, sku, size, qty, amount, account, reason,
         requested_by, today),
    )
    conn.commit()
    pending_after = _pending_total(conn, account)
    projected = cash["balance"] - pending_after
    return {
        "created": True,
        "request_id": cur.lastrowid,
        "status": "pending",
        "kind": kind,
        "amount": amount,
        "account": account,
        "cash_balance_now": cash["balance"],
        "all_pending_on_account": pending_after,
        "projected_balance_if_all_approved": projected,
        "warning": (
            "If every pending request is approved the account would go negative; "
            "the pay step will refuse whichever one does not fit. Tell the Boss to prioritize."
            if projected < 0 else None
        ),
        "message": "Waiting for human approval. Nothing has been paid.",
    }


# ---------------------------------------------------------------------------
# Tickets and shop date
# ---------------------------------------------------------------------------

@mcp.tool()
def get_shop_date() -> dict:
    """Return the shop's 'today' (desk.date_today) and desk notes.

    Reads the desk table. Always use this date - not the real-world date - to
    decide what is overdue or due soon.
    """
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
        return dict(row)


@mcp.tool()
def list_open_tickets() -> list[dict]:
    """List every ticket on the board that is not resolved yet.

    Reads the tickets table.
    """
    with _connect() as conn:
        return _rows(conn.execute(
            "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY created_at"
        ))


@mcp.tool()
def list_tickets() -> list[dict]:
    """List every ticket on the board, resolved or not, oldest first.

    Reads the tickets table.
    """
    with _connect() as conn:
        return _rows(conn.execute("SELECT * FROM tickets ORDER BY created_at"))


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with all its fields (type, requester, sku, size, qty, lease_id,
    invoice_id, status, notes).

    Reads the tickets table.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"found": False, "ticket_id": ticket_id, "message": "No ticket with this id."}
        return {"found": True, **dict(row)}


@mcp.tool()
def update_ticket(ticket_id: int,
                  status: Literal["open", "in_progress", "waiting_approval", "resolved"],
                  note: str, updated_by: str) -> dict:
    """Set a ticket's status and append a dated note to it. Boss uses this to record
    final calls.

    Updates the tickets table (status, notes).
    """
    with _connect() as conn:
        row = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"updated": False, "message": "No ticket with this id."}
        today = _date_today(conn)
        notes = (row["notes"] or "") + f"\n[{today} {updated_by}] {note}"
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
                     (status, notes.strip(), ticket_id))
        conn.commit()
        return {"updated": True, "ticket_id": ticket_id, "status": status}


# ---------------------------------------------------------------------------
# Inventory, pricing, vendors
# ---------------------------------------------------------------------------

@mcp.tool()
def check_stock(sku: str, size: str, qty_needed: int) -> dict:
    """Check on-hand stock for one SKU and size and report any shortfall.

    Reads the inventory table. Use for customer orders and bulk requests to see
    whether the requested quantity can be filled from stock.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if row is None:
            return {"found": False, "sku": sku, "size": size,
                    "message": "No inventory row for this SKU and size."}
        on_hand = row["qty"]
        return {
            "found": True,
            "sku": row["sku"],
            "name": row["name"],
            "size": row["size"],
            "location": row["location"],
            "qty_on_hand": on_hand,
            "qty_needed": qty_needed,
            "shortfall": max(qty_needed - on_hand, 0),
            "can_fill_from_stock": on_hand >= qty_needed,
        }


@mcp.tool()
def list_inventory(sku: str | None = None) -> list[dict]:
    """List stock rows (every size) for one SKU, or the whole shop if sku is omitted.

    Reads the inventory table. Useful for offering a customer another size.
    """
    with _connect() as conn:
        if sku:
            return _rows(conn.execute(
                "SELECT * FROM inventory WHERE sku = ? ORDER BY size", (sku,)))
        return _rows(conn.execute("SELECT * FROM inventory ORDER BY sku, size"))


@mcp.tool()
def get_pricing(sku: str) -> dict:
    """Get unit cost and list price for a SKU.

    Reads the pricing table.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if row is None:
            return {"found": False, "sku": sku, "message": "No pricing row for this SKU."}
        return {"found": True, **dict(row)}


@mcp.tool()
def check_margin(sku: str, unit_price: float, qty: int) -> dict:
    """Work out the margin if a SKU is sold at a proposed unit price (e.g. a discount).

    Reads the pricing table. Returns discount vs. list price, profit per unit and in
    total, margin percent, and whether the price is below cost.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if row is None:
            return {"found": False, "sku": sku, "message": "No pricing row for this SKU."}
        cost, list_price = row["unit_cost"], row["list_price"]
        profit = unit_price - cost
        return {
            "found": True,
            "sku": sku,
            "qty": qty,
            "unit_cost": cost,
            "list_price": list_price,
            "proposed_unit_price": unit_price,
            "discount_pct_vs_list": round((list_price - unit_price) / list_price * 100, 2),
            "profit_per_unit": round(profit, 2),
            "margin_pct": round(profit / unit_price * 100, 2) if unit_price else None,
            "total_revenue": round(unit_price * qty, 2),
            "total_cost": round(cost * qty, 2),
            "total_profit": round(profit * qty, 2),
            "below_cost": unit_price < cost,
        }


@mcp.tool()
def list_vendors() -> list[dict]:
    """List all vendors with their specialty and lead time in days.

    Reads the vendors table. Lead times must come from here.
    """
    with _connect() as conn:
        return _rows(conn.execute("SELECT * FROM vendors ORDER BY id"))


@mcp.tool()
def check_vendor_status(vendor_id: int) -> dict:
    """Look up a vendor's lead time and any unpaid invoices that block shipping.

    Reads the vendors and invoices tables (and desk.date_today to flag overdue).
    A vendor will not ship new product while it has an open unpaid invoice.
    """
    with _connect() as conn:
        today = _date_today(conn)
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
            (vendor_id,),
        ).fetchone()
        if vendor is None:
            return {"found": False, "vendor_id": vendor_id,
                    "message": "No vendor with this id."}
        open_invoices = _open_invoices(conn, vendor_id, today)
        return {
            "found": True,
            "date_today": today,
            "vendor_id": vendor["id"],
            "name": vendor["name"],
            "specialty": vendor["specialty"],
            "lead_days": vendor["lead_days"],
            "open_invoices": open_invoices,
            "open_balance": sum(inv["amount"] for inv in open_invoices),
            "will_ship": len(open_invoices) == 0,
        }


# ---------------------------------------------------------------------------
# Money: cash, invoices, leases
# ---------------------------------------------------------------------------

@mcp.tool()
def get_cash_balance(account: str = "checking") -> dict:
    """Get a cash account's balance, plus the total of payment requests still pending
    on it and what would be left if all were approved.

    Reads the cash_accounts and payment_requests tables. No revenue is modeled:
    cash only goes out.
    """
    with _connect() as conn:
        cash = _cash(conn, account)
        if cash is None:
            return {"found": False, "account": account, "message": "No such cash account."}
        pending = _pending_total(conn, account)
        return {
            "found": True,
            **dict(cash),
            "pending_requests_total": pending,
            "projected_balance_if_all_approved": cash["balance"] - pending,
        }


@mcp.tool()
def get_invoice(invoice_id: int) -> dict:
    """Get one invoice with its vendor name and whether it is overdue as of shop today.

    Reads the invoices, vendors, and desk tables.
    """
    with _connect() as conn:
        today = _date_today(conn)
        row = conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        if row is None:
            return {"found": False, "invoice_id": invoice_id, "message": "No invoice with this id."}
        inv = dict(row)
        days_past_due = conn.execute(
            "SELECT CAST(julianday(?) - julianday(?) AS INTEGER) AS d",
            (today, inv["due_date"]),
        ).fetchone()["d"]
        return {
            "found": True,
            "date_today": today,
            **inv,
            "overdue": inv["status"] == "open" and days_past_due > 0,
            "days_past_due": max(days_past_due, 0),
        }


@mcp.tool()
def list_open_invoices() -> list[dict]:
    """List every open (unpaid) invoice across all vendors, oldest due date first.

    Reads the invoices, vendors, and desk tables.
    """
    with _connect() as conn:
        today = _date_today(conn)
        rows = _rows(conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open' ORDER BY i.due_date"
        ))
        return [{**r, "overdue": r["due_date"] < today} for r in rows]


@mcp.tool()
def get_lease(lease_id: int) -> dict:
    """Get a lease's rent amount and due date, with days until due.

    Reads the leases table (and desk.date_today). Use for rent notices to confirm
    how much is owed, to whom, and how soon.
    """
    with _connect() as conn:
        today = _date_today(conn)
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
            "FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"found": False, "lease_id": lease_id,
                    "message": "No lease with this id."}
        days_until_due = conn.execute(
            "SELECT CAST(julianday(?) - julianday(?) AS INTEGER) AS d",
            (lease["next_due"], today),
        ).fetchone()["d"]
        return {
            "found": True,
            "date_today": today,
            **dict(lease),
            "days_until_due": days_until_due,
            "overdue": days_until_due < 0,
        }


# ---------------------------------------------------------------------------
# Payment requests (agents propose; a human approves)
# ---------------------------------------------------------------------------

@mcp.tool()
def request_invoice_payment(invoice_id: int, ticket_id: int, reason: str,
                            requested_by: str, account: str = "checking") -> dict:
    """Prepare a payment of an open vendor invoice FOR HUMAN APPROVAL. Pays nothing.

    Reads invoices and cash_accounts; inserts a pending row into payment_requests.
    The amount is the invoice amount from the database.
    """
    with _connect() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if inv is None:
            return {"created": False, "message": "No invoice with this id."}
        if inv["status"] != "open":
            return {"created": False, "message": f"Invoice is already {inv['status']}."}
        return _create_request(
            conn, ticket_id=ticket_id, kind="invoice", ref_id=invoice_id,
            vendor_id=inv["vendor_id"], sku=None, size=None, qty=None,
            amount=inv["amount"], account=account, reason=reason, requested_by=requested_by,
        )


@mcp.tool()
def request_rent_payment(lease_id: int, ticket_id: int, reason: str,
                         requested_by: str, account: str = "checking") -> dict:
    """Prepare this month's rent payment for a lease FOR HUMAN APPROVAL. Pays nothing.

    Reads leases and cash_accounts; inserts a pending row into payment_requests.
    The amount is leases.monthly_rent from the database.
    """
    with _connect() as conn:
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if lease is None:
            return {"created": False, "message": "No lease with this id."}
        return _create_request(
            conn, ticket_id=ticket_id, kind="rent", ref_id=lease_id, vendor_id=None,
            sku=None, size=None, qty=None, amount=lease["monthly_rent"], account=account,
            reason=reason, requested_by=requested_by,
        )


@mcp.tool()
def request_purchase_order(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int,
                           reason: str, requested_by: str, account: str = "checking") -> dict:
    """Prepare a restock purchase order FOR HUMAN APPROVAL. Orders and pays nothing.

    Reads vendors, invoices, pricing, and cash_accounts; inserts a pending row into
    payment_requests. The amount is qty x pricing.unit_cost. Warns if the vendor is
    blocked by an open invoice (the order cannot be approved until that is paid).
    """
    if qty <= 0:
        return {"created": False, "message": "qty must be positive."}
    with _connect() as conn:
        today = _date_today(conn)
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"created": False, "message": "No vendor with this id."}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"created": False, "message": "No pricing row for this SKU."}
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?",
                        (sku, size)).fetchone() is None:
            return {"created": False, "message": "No inventory row for this SKU and size."}
        result = _create_request(
            conn, ticket_id=ticket_id, kind="purchase_order", ref_id=None, vendor_id=vendor_id,
            sku=sku, size=size, qty=qty, amount=round(qty * price["unit_cost"], 2),
            account=account, reason=reason, requested_by=requested_by,
        )
        blocking = _open_invoices(conn, vendor_id, today)
        if result.get("created"):
            result["vendor_lead_days"] = vendor["lead_days"]
            if blocking:
                result["vendor_blocked_by_invoices"] = [b["id"] for b in blocking]
                result["blocked_note"] = (
                    "Vendor will not ship while these invoices are open. This order can only "
                    "be approved after they are paid."
                )
        return result


@mcp.tool()
def list_payment_requests(status: Literal["pending", "approved", "rejected", "refused"] | None = None,
                          ticket_id: int | None = None) -> list[dict]:
    """List payment requests, optionally filtered by status and/or ticket.

    Reads the payment_requests table.
    """
    sql, args = "SELECT * FROM payment_requests WHERE 1=1", []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if ticket_id is not None:
        sql += " AND ticket_id = ?"
        args.append(ticket_id)
    with _connect() as conn:
        return _rows(conn.execute(sql + " ORDER BY id", args))


@mcp.tool()
def approve_payment_request(request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Approve a pending payment request and pay it.

    Refuses if cash would go negative or (for purchase orders) the vendor still has an
    open invoice. On success, in one transaction: inserts into payments, lowers
    cash_accounts.balance, and marks the invoice paid (invoice) or moves
    leases.next_due forward one month (rent).
    """
    approver = approved_by.strip()
    if not approver or approver.lower().replace(" ", "_") in AGENT_NAMES:
        return {"paid": False, "message": "approved_by must be a human's name, not an agent."}
    with _connect() as conn:
        req = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"paid": False, "message": "No payment request with this id."}
        if req["status"] != "pending":
            return {"paid": False, "message": f"Request is already {req['status']}."}
        today = _date_today(conn)

        def refuse(why: str) -> dict:
            conn.execute(
                "UPDATE payment_requests SET status = 'refused', decided_by = ?, decided_at = ?, "
                "decision_note = ? WHERE id = ?", (approver, today, why, request_id))
            conn.commit()
            return {"paid": False, "request_id": request_id, "status": "refused", "message": why}

        cash = _cash(conn, req["account"])
        if cash is None:
            return refuse(f"No cash account named {req['account']!r}.")
        if cash["balance"] < req["amount"]:
            return refuse(
                f"Not enough cash: balance {cash['balance']:.2f} < amount {req['amount']:.2f}. "
                "No negative balances."
            )
        if req["kind"] == "invoice":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (req["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                return refuse("Invoice is no longer open.")
        if req["kind"] == "purchase_order":
            blocking = _open_invoices(conn, req["vendor_id"], today)
            if blocking:
                return {"paid": False, "request_id": request_id, "status": "pending",
                        "message": "Vendor still has open invoices "
                                   f"{[b['id'] for b in blocking]}; pay those first."}

        new_balance = round(cash["balance"] - req["amount"], 2)
        ref_id = req["ref_id"] if req["kind"] != "purchase_order" else request_id
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], ref_id, req["amount"], req["account"], today, approver),
        )
        payment_id = cur.lastrowid
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                     (new_balance, today, req["account"]))
        if req["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
        elif req["kind"] == "rent":
            conn.execute("UPDATE leases SET next_due = date(next_due, '+1 month') WHERE id = ?",
                         (req["ref_id"],))
        conn.execute(
            "UPDATE payment_requests SET status = 'approved', decided_by = ?, decided_at = ?, "
            "payment_id = ? WHERE id = ?", (approver, today, payment_id, request_id))
        conn.commit()
        return {"paid": True, "request_id": request_id, "payment_id": payment_id,
                "kind": req["kind"], "amount": req["amount"], "account": req["account"],
                "new_balance": new_balance, "approved_by": approver}


@mcp.tool()
def reject_payment_request(request_id: int, decided_by: str, reason: str) -> dict:
    """HUMAN ONLY. Reject a pending payment request. Nothing is paid.

    Updates the payment_requests table.
    """
    with _connect() as conn:
        req = conn.execute("SELECT status FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"rejected": False, "message": "No payment request with this id."}
        if req["status"] != "pending":
            return {"rejected": False, "message": f"Request is already {req['status']}."}
        conn.execute(
            "UPDATE payment_requests SET status = 'rejected', decided_by = ?, decided_at = ?, "
            "decision_note = ? WHERE id = ?",
            (decided_by, _date_today(conn), reason, request_id))
        conn.commit()
        return {"rejected": True, "request_id": request_id}


# ---------------------------------------------------------------------------
# Drafts (nothing is ever sent)
# ---------------------------------------------------------------------------

@mcp.tool()
def save_draft(ticket_id: int,
               kind: Literal["customer_message", "vendor_message", "landlord_message", "internal_note"],
               recipient: str, subject: str, body: str, author: str) -> dict:
    """Save a draft message on the board for a human to review. Never sends anything.

    Inserts into the drafts table.
    """
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, kind, recipient, subject, body, author, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, kind, recipient, subject, body, author, _date_today(conn)),
        )
        conn.commit()
        return {"saved": True, "draft_id": cur.lastrowid, "sent": False}


@mcp.tool()
def list_drafts(ticket_id: int | None = None) -> list[dict]:
    """List saved drafts, optionally for one ticket.

    Reads the drafts table.
    """
    with _connect() as conn:
        if ticket_id is not None:
            return _rows(conn.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id",
                                      (ticket_id,)))
        return _rows(conn.execute("SELECT * FROM drafts ORDER BY id"))


if __name__ == "__main__":
    mcp.run(show_banner=False)
