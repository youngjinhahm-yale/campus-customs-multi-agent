# Dashboard design: Campus Customs *Back Office*

The dashboard (`frontend/`, React + Vite + TypeScript) is designed as the **back office of a campus shop on Chapel Street in New Haven**, dressed in **Yale's identity**: Yale Blue, Yale's secondary palette, a heritage serif, and the motto *Lux et Veritas*. A person sits with five agents, one cash register, and a pen. It shouldn't feel like a monitoring console. Everything on screen maps to an object a shop owner already understands: a bulletin board of tickets, a room of colleagues talking, a till, and a tray of things waiting for a signature.

### Yale identity
- **Yale Blue `#00356B`** is the anchor colour: the header banner, the bulletin board, the till, primary buttons, the RESOLVED stamp ink, and the footer band. A thin **light-blue rule (`#63AAFF`)** under the header and on the footer echoes the stripe on a Yale banner.
- **Shield mark:** a white shield shape drawn in CSS with the shop's "CC" monogram in serif. It nods to a college crest without copying Yale's trademarked logo.
- **Motto:** *Lux et Veritas · New Haven, Connecticut* sits in small caps above the title, and again in the footer.
- **Handsome Dan:** Yale's bulldog appears in the empty state ("Handsome Dan is napping") and the footer ("Handsome Dan approves of human sign-off"), a small bit of campus warmth.
- **Cool, bright background** (`#F5F7FB`) with a faint Yale-blue wash at the top, white cards, and blue-grey lines, so the blue elements stand out.

Run it with `npm run dev` in `frontend/` (opens http://localhost:5173). It talks to the FastAPI backend at `http://localhost:8000`, which allows the Vite origin through CORS.

---

## Layout: three columns, left to right like the work itself

| Left: **The Board** | Center: **The Floor** | Right: **The Till & the tray** |
|---|---|---|
| The tickets, pinned to a Yale-blue bulletin board | The agents working the selected ticket, live | The money, and what needs your signature |

The columns follow a ticket's life. You pick a card on the left, watch the team work it in the middle, and sign for the money on the right. Your eye moves the same direction the ticket does. The board and the side column are sticky, so the cash and the approvals stay in view while the transcript scrolls.

### The Board (tickets)
- The board is a **Yale-blue felt bulletin board**. Each ticket is a white **index card** with a blue-and-white pushpin, faint blue ruled lines, and a slight random tilt, so the board feels handled rather than generated. The selected card straightens up and gets a light-blue outline.
- Cards show the type (🛍️ order, 🏠 rent, 🏷️ discount), requester, the note in italics, and mono "tags" for SKU, size, qty, lease and invoice links.
- A status chip shows the ticket's state. While the team works, it becomes a pulsing **"Team at work"** chip. A red **"✍️ 1 to sign"** chip appears when that ticket has a payment waiting on you.
- **Resolved tickets get a rubber stamp.** When the run finishes, a double-bordered **RESOLVED** stamp in Yale-blue ink slams onto the card (a quick scale-down animation with multiply blending, so it looks inked), and the pin turns deep blue. You can read the whole board's status from across the room.
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
Each agent has a fixed **colour, glyph and role line**, used everywhere (roster, bubbles, handoff chips, report cards, rails). All five colours come from **Yale's official palette**:

| Agent | Glyph | Colour | Why |
|---|---|---|---|
| Boss | 🧭 | Yale Blue `#00356B` | The compass that sets direction. Gets Yale's own colour. |
| Inventory | 📦 | Yale green `#5F712D` | Stockroom and shelves; green for "in stock". |
| Accounting | 🧾 | Yale orange `#BD5319` | Receipts and caution around money. |
| Facilities | 🏛️ | Yale stone grey `#7A6F66` | The building and the landlord, like New Haven stonework. |
| Customer Service | 💬 | Yale secondary blue `#286DC0` | The friendly, customer-facing voice; a lighter blue than the Boss. |

The hues are spread across blue, green, orange and grey, so the transcript can be scanned by colour, and the glyph backs up the colour for anyone who can't tell the colours apart.

### The Till (cash)
- The checking balance is shown on a **cash-register display**: a deep Yale-blue panel with white mono digits that glow light blue.
- **It counts down when a payment clears.** After you approve a payment, the number rolls down to the new balance with an eased animation, and a red **−$840.00** floats up and fades out. The drop is *felt*, not just updated.
- Under the display, a bar shows how much of the balance is **already claimed by pending requests** (light blue, turning red if pending requests would overdraw), with "Waiting to sign $3,240" and "If all signed $160". That makes the cross-ticket cash squeeze obvious before you sign anything.
- A small note says cash only goes out and the till refuses anything below $0. The rule is visible, not hidden.

### Needs your signature (human approval)
- Payments and POs the agents prepared appear as **white vouchers with a Yale-blue edge**: kind, voucher number, a big serif amount, invoice/lease/SKU, the ticket, *"Prepared by 🧾 Accounting"*, and the agent's one-line reason.
- **"Signing as"** is a handwritten-style name line. The Approve and Reject buttons stay disabled until you type your name, because the backend refuses an empty or agent name, and because signing should feel deliberate. The name is remembered for next time.
- **Approve & pay** (in Yale Blue) is the only control that moves money. If the till refuses (not enough cash, vendor still blocked), a red toast says exactly why. A small **ledger** below keeps the last decisions (approved / refused / rejected, and by whom).

### Outbox
- The drafts the agents wrote are folded **letters**. You click to open one, and each is stamped **DRAFT · NOT SENT** in red. Nothing in the UI can send them, which matches the shop rule.

### Other details
- The top bar has a live **backend connected** light and a **↺ Reset shop** button (with a confirm) for fresh runs. Reset is disabled while a ticket is running.
- Toasts confirm each action in plain words ("Paid. Checking is now $2,560.00.", "Ticket #101 resolved — see the shift report.").
- Responsive: on narrower screens the till and tray move under the floor, and on phones everything stacks.

---

## Why these choices

- **Real-world metaphors lower the learning curve.** Anyone who has worked a shop counter knows what a bulletin board, a till and a signature mean. No legend is needed.
- **Trust comes from seeing the work.** Showing each tool call and its result next to the agent's words lets a person check *why* an agent said "0 in stock" before signing anything.
- **The human stays in charge of money, visibly.** The signature tray is physically separate from the agents' floor, the agents can only fill it, and approval needs your name. The UI reinforces the rule the backend enforces.
- **Delegation should be legible.** Indented, colour-railed threads and handoff cards make "full connectivity" something you can watch, including specialist-to-specialist handoffs, instead of a flat log.
- **Small moments make it pleasant to sit at:** the stamp landing on a finished ticket, the till rolling down, the pulsing desk lights. They give feedback at exactly the moments that matter (a ticket done, money spent) without adding noise elsewhere.
- **It looks like it belongs at Yale.** One strong brand colour (Yale Blue) holds the whole desk together, and the agents use Yale's own secondary colours, so the screen feels like part of campus rather than a generic admin panel. Red is saved for "needs you / refused".
- **Calm and bright.** White cards on a cool background keep long sessions easy on the eyes and let the blue do the talking.

## Typography
- **Libre Caslon Text** (serif) for headings, ticket titles, amounts, letters and the small-caps motto: a classic book face in the spirit of Yale's own serif typeface.
- **Inter** for body text: clean and readable at small sizes.
- **JetBrains Mono** for tool calls, SKUs and the till digits: data looks like data.
