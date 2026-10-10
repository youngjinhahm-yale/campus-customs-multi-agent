# Dashboard design: Campus Customs *Back Office*

The dashboard (`frontend/`, React + Vite + TypeScript) is designed as the **back office of a small campus shop**: a warm paper desk where a person sits with five agents, one cash register, and a pen. It shouldn't feel like a monitoring console. Everything on screen maps to an object a shop owner already understands: a corkboard of tickets, a room of colleagues talking, a till, and a tray of things waiting for a signature.

Run it with `npm run dev` in `frontend/` (opens http://localhost:5173). It talks to the FastAPI backend at `http://localhost:8000`, which allows the Vite origin through CORS.

---

## Layout: three columns, left to right like the work itself

| Left: **The Board** | Center: **The Floor** | Right: **The Till & the tray** |
|---|---|---|
| The tickets, pinned to a corkboard | The agents working the selected ticket, live | The money, and what needs your signature |

The columns follow a ticket's life. You pick a card on the left, watch the team work it in the middle, and sign for the money on the right. Your eye moves the same direction the ticket does. The board and the side column are sticky, so the cash and the approvals stay in view while the transcript scrolls.

### The Board (tickets)
- Each ticket is an **index card pinned to cork**, with a red pushpin, faint ruled lines, and a slight random tilt, so the board feels handled rather than generated. The selected card straightens up and gets a Yale-blue outline.
- Cards show the type (🛍️ order, 🏠 rent, 🏷️ discount), requester, the note in italics, and mono "tags" for SKU, size, qty, lease and invoice links.
- A status chip shows the ticket's state. While the team works, it becomes a pulsing **"Team at work"** chip. A red **"✍️ 1 to sign"** chip appears when that ticket has a payment waiting on you.
- **Resolved tickets get a rubber stamp.** When the run finishes, a green double-bordered **RESOLVED** stamp slams onto the card (a quick scale-down animation with multiply blending, so it looks inked), and the pushpin turns green. You can read the whole board's status from across the room.
- The hint at the bottom says to run in order 101 → 102 → 103, because the tickets share one checking account.

### The Floor (agents at work)
- **Roster of five desks** across the top. Each agent has a nameplate with its glyph, name and a live status line ("Using check_stock", "Waiting on Inventory", "Done", "Not on this ticket"), plus a status light that pulses in the agent's colour while working, turns amber while waiting on a teammate, and turns green when done. Agents not needed on a ticket fade out, so you can *see* that the Boss didn't send everyone.
- **The transcript** below reads like a group chat:
  - **Speech bubbles** for what an agent says, with its tool calls shown as dashed mono "receipts" (`⚙ check_stock(sku: "CC-TEE-WHITE", size: "S", qty_needed: 1)`), and a one-line gist of what each tool returned (`↳ check_stock qty_on_hand=0 · shortfall=1`).
  - **Handoff cards** for delegation: two coloured name chips with an arrow (🧭 Boss → 📦 Inventory) and the task quoted in italic serif, like a note passed across a desk.
  - **Threading by depth.** Work done inside a delegation is indented with a coloured rail in the sub-agent's colour, so the full-connectivity chain (e.g., Customer Service → Inventory inside Boss → Customer Service) is visible at a glance.
  - **Report bubbles** with a heavier border when an agent hands back its result, and a "Final call" tag on the Boss's decision.
  - Run start and finish are quiet dividers. A three-dot "typing" indicator bounces while the run is live, and the view auto-scrolls to the newest line.
- **Shift report** appears under the transcript when a run finishes:
  - **The Boss's call** in a blue-ruled callout, with the status tag and a numbered **"For you"** list of next steps for the human.
  - **One card per specialist who worked the ticket**, topped with that agent's colour: its summary, blockers (⚠️), the tools it used with counts (`check_stock ×2`), and what it produced (💵 request #1, ✉️ draft #1).
  - A line naming who **wasn't needed** ("Not needed on this ticket: Facilities").
  - The run's cost (model calls, tool calls, tokens), so token use stays visible.

### How the agents read differently
Each agent has a fixed **colour, glyph and role line**, used everywhere (roster, bubbles, handoff chips, report cards, rails):

| Agent | Glyph | Colour | Why |
|---|---|---|---|
| Boss | 🧭 | Yale navy | The compass that sets direction. Gets the shop's own colour. |
| Inventory | 📦 | Green | Stockroom and shelves; green for "in stock". |
| Accounting | 🧾 | Amber | Receipts and caution around money. |
| Facilities | 🏛️ | Purple | The building, the landlord; calm and formal. |
| Customer Service | 💬 | Terracotta | The warm, human-facing voice. |

The colours are far apart on the wheel, so the transcript can be scanned by colour alone, and the glyph backs up the colour for anyone who can't tell the colours apart.

### The Till (cash)
- The checking balance is shown on a **cash-register display**: a dark brushed panel with green LED-style mono digits that glow slightly.
- **It counts down when a payment clears.** After you approve a payment, the number rolls down to the new balance with an eased animation, and a red **−$840.00** floats up and fades out. The drop is *felt*, not just updated.
- Under the display, a bar shows how much of the balance is **already claimed by pending requests** (amber, turning red if pending requests would overdraw), with "Waiting to sign $3,240" and "If all signed $160". That makes the cross-ticket cash squeeze obvious before you sign anything.
- A small note says cash only goes out and the till refuses anything below $0. The rule is visible, not hidden.

### Needs your signature (human approval)
- Payments and POs the agents prepared appear as **cream vouchers with a perforated edge**: kind, voucher number, a big serif amount, invoice/lease/SKU, the ticket, *"Prepared by 🧾 Accounting"*, and the agent's one-line reason.
- **"Signing as"** is a handwritten-style name line. The Approve and Reject buttons stay disabled until you type your name, because the backend refuses an empty or agent name, and because signing should feel deliberate. The name is remembered for next time.
- **Approve & pay** is the only control that moves money. If the till refuses (not enough cash, vendor still blocked), a red toast says exactly why. A small **ledger** below keeps the last decisions (approved / refused / rejected, and by whom).

### Outbox
- The drafts the agents wrote are folded **letters**. You click to open one, and each is stamped **DRAFT · NOT SENT** in red. Nothing in the UI can send them, which matches the shop rule.

### Other details
- The top bar has a live **backend connected** light and a **↺ Reset shop** button (with a confirm) for fresh runs. Reset is disabled while a ticket is running.
- Toasts confirm each action in plain words ("Paid. Checking is now $2,560.00.", "Ticket #101 resolved — see the shift report.").
- Responsive: on narrower screens the till and tray move under the floor, and on phones everything stacks.

---

## Why these choices

- **Real-world metaphors lower the learning curve.** Anyone who has worked a shop counter knows what a corkboard, a till and a signature mean. No legend is needed.
- **Trust comes from seeing the work.** Showing each tool call and its result next to the agent's words lets a person check *why* an agent said "0 in stock" before signing anything.
- **The human stays in charge of money, visibly.** The signature tray is physically separate from the agents' floor, the agents can only fill it, and approval needs your name. The UI reinforces the rule the backend enforces.
- **Delegation should be legible.** Indented, colour-railed threads and handoff cards make "full connectivity" something you can watch, including specialist-to-specialist handoffs, instead of a flat log.
- **Small moments make it pleasant to sit at:** the stamp landing on a finished ticket, the till rolling down, the pulsing desk lights. They give feedback at exactly the moments that matter (a ticket done, money spent) without adding noise elsewhere.
- **Calm palette, one loud colour per meaning.** The warm paper and cork background keeps long sessions easy on the eyes. Strong colour is saved for the agents, green for "done/paid", and red for "needs you / refused".

## Typography
- **Libre Caslon Text** (serif) for headings, ticket titles, amounts and letters: Yale's heritage feel and a "paper" voice.
- **Inter** for body text: clean and readable at small sizes.
- **JetBrains Mono** for tool calls, SKUs and the till digits: data looks like data.
