# AI Prompts Log — HW5: Campus Customs Multi-Agent Operations

This file logs the prompts I typed to my vibe coder (Claude Code), one section per problem.

---

## Setup (before Problem 1)

**Prompts:**
> do joke on hw5, and there is where you put your work today

> this is scenario. Don't do anything yet. just understand the situation

> you have data.zip

**Notes:** I shared the scenario, data, and shop rules as context only, and told the coder not to build anything until I gave it a problem.

---

## Problem 1: Vibe coder prompts

**Prompt:**
> Now let's go
>
> Problem 1: Vibe coder prompts
>
> Create AI_prompts.md at the start of the assignment and keep it updated as you work. This file is the log of what you typed to your vibe coder.
>
> Describe each problem to your vibe coder in your own words. Do not paste this whole page or the assignment URL and ask it to do everything for you. Put one section for each problem. Each section must include:
>
> * The problem number and title
> * At elast one prompt you typed, in your own words as much as possible
> * One follow-up prompt if you needed it (and one sentence on what was lacking after the first)

**Follow-up prompt:**
> then solve all of them

**What was lacking after the first:** The coder had logged its own paraphrases of my prompts instead of what I actually typed, so I had it replace them with my real messages.

---

## Problem 2: Study the Campus Customs database

**Prompt:**
> Problem 2: Study the Campus Custom database
>
> Open data/campus_customs.db and look through every table and its fields. Copy the original file to data/campus_customs_new.db - later problem update what that working copy.
>
> Study the three open tickets so you see how they link to other tables. Start output/harness.md. For each table, list the fields and one short line on why that table matters for the agents.
>
> You will keep growing this harness file in later problems

**Follow-up prompt:** None needed. The coder unzipped the data, made the working copy, and wrote output/harness.md with every table, the ticket links, and the cash squeeze across tickets.

---

## Problem 3: Build the MCP server

**Prompt:**
> Problem 3: Build the MCP server
>
> Write an MCP server in mcp_server/ using FastMCP. It will talk to data/campus_customs_new.db. You do not need to connect or run it in this problem. Every agent in this homework uses the tools in this MCP server. You will add more tools to it later; for now write three tools you know you will need for the tickets in the database. Keep the names clear. Never invent any data, only use information in the database. In output/harness.md, list each of your three MCP tools. For every tool include: which table it reads, which ticket it helps unlock (101, 102, or 103), and one sentence on why that tool is the right one for that ticket. Vague lines like "read inventory" score low - tie the tools to the ticket.
>
> Also add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the three tools it has.

**Follow-up prompt:** None needed. The coder wrote mcp_server/server.py with check_stock, check_vendor_status, and get_lease, plus the README and the harness section.

---

## Problem 4: Add the MCP server to vibe coder and test each tool

**Prompt:**
> Problem 4: Add the MCP server to vibe coder and test each tool
>
> In your vibe coder (Claude code). add your MCP server to this project so the vibe coder can call the tools. Save the connection JSON text in .mcp.json at the project root (or however your vibe coder saves local MCP server lists). With your vibe coder connected, test each of your three MCP tools. Save the evidence in output/mcp_smoke.json. For every tool include:
>
> * the prompt you asked the vibe coder
> * the tool name
> * the tool output (must match values in data/campus_customs_new.db)

**Follow-up prompt** (new session, after restarting Claude Code so it loaded the MCP server):
> Problem 4: my campus-customs MCP server should be connected now. Work in the hw5 folder.
>
> Test each of my three MCP tools through your MCP connection (not a Python script):
> 1. check_stock for CC-TEE-WHITE size S, qty needed 1 (ticket 101)
> 2. check_vendor_status for vendor 1 (ticket 101)
> 3. get_lease for lease 1 (ticket 102)
>
> Save the evidence in hw5/output/mcp_smoke.json. For each tool include the prompt I asked, the tool name, the arguments, and the exact tool output. Then read hw5/data/campus_customs_new.db and confirm each output matches the database, and note that in the file too.
>
> After that, add this prompt to the Problem 4 section of hw5/AI_prompts.md. Last, remove the temporary campus-customs entry from the .mcp.json in the AI Foundations yo folder, but keep hw5/.mcp.json and leave the other servers alone.

**What was lacking after the first:** Claude Code only loads a new MCP server when a session starts, so the first session could add `.mcp.json` but could not call the tools through the connection. After a restart, the three tools were called through MCP and all outputs matched the database (see `output/mcp_smoke.json`).

---

## Problem 5: Build the agent team and grow the MCP tools

**Prompt:**
> Problem 5: Build the agent team and grow the MCP tools
>
> Build the agentic team for Campus Customs using PydanticAI : Boss, Inventory, Accounting, Facilities, and Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity.
>
> Put the agent prompts in backend/prompts/ - one file per agent. Put data types in backend/models.py, and the agent files under backend/ (your layout can vary as long as the five roles are clear). Use your PORTKEY_API_KEY and only gpt-6-luna for every agent.
>
> Write each prompt in your own words with the shop rules that agent needs. More detailed prompt that cover all aspects of an agent's work and scope score higher than a short generic prompt.
>
> Add any tools the agents need to your MCP server so they can work on the open tickets. Shop facts come from the MCP server over data/capus_customs_new.db - do not invent a second shop-tools layer that bypasses MCP.
>
> write the agents so they append to output/audit_trails.json as they run: for each agent-loop step, record enough to audit later. Append to this file - do not wipe it each run.
>
> In output/harness.md, list each agent and each MCP tool (including ones you add in this problem) along with which table the tools uses. Also add a short safety section: the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check.
>
> Update mcp_server/README.md so the tool list matches what you have now.

**Follow-up prompts:**
> did you follow every instructions I gave to you?

> then solve all of them

**What was lacking after the first:** The command-line runner read the open-ticket list straight from SQLite instead of through the MCP server, which broke the "no second shop-tools layer" rule. The coder switched it to the `list_open_tickets` MCP tool.

> so you did everything I gave you?

> do that

**What was lacking:** The agents had only been tested offline, so `output/audit_trails.json` didn't exist yet. The coder reset the database and ran all three tickets through the team with gpt-6-luna. The result was 186 audit events, 2 pending payment requests, 3 unsent drafts, and no payments made.

> when it comes to prompt, change the prompt in my own words

**What was lacking:** The five agent prompts read like formal documentation, not how I'd brief my team. The coder rewrote them in my plain first-person voice, as a VP staffing a deal team, keeping every tool name, shop rule and handoff.

---

## Problem 6: Plan the three tickets

**Prompt:**
> Problem 6: before the agents run again, I want to write down my plan for the three tickets so I can compare it with what actually happens later.
>
> Build output/desk_tickets.html as a single file I can double-click to open (no outside libraries, works offline). It should have tabs for 101, 102, 103, Cash, and Reflection. Cash and Reflection just say "coming later" for now. Each ticket tab gets an "Expected" section with my plan and an empty "Actual" section that says "to be filled after the run".
>
> My plan for each ticket:
>
> 101 (tee, size S): Boss should call Inventory first, because the first question is whether we can fill the order; if the tee were in stock, no money would be involved. I expect Inventory to find 0 in stock and see that Bulldog Print Co is blocked by overdue invoice 501. Then Boss calls Accounting to prepare the $840 payment for my approval, then Customer Service to draft a delay message with no firm date. No Facilities. I think no new purchase order is needed, because invoice 501 is the reprint of this exact tee. Tools I expect: get_ticket, get_shop_date, check_stock, list_vendors, check_vendor_status, get_invoice, get_cash_balance, request_invoice_payment, save_draft, update_ticket.
>
> 102 (rent): Boss should call Facilities first, because Facilities owns the lease and the amount and date should come from the lease record, not the email. I expect Facilities to confirm $2,400 due 09-02 and then hand off to Accounting directly to file the rent request (a specialist calling a specialist). No Inventory and no Customer Service, because the requester is the landlord and no product is involved. Tools: get_ticket, get_lease, list_payment_requests, get_cash_balance, request_rent_payment, save_draft, update_ticket. After 101 and 102, cash would only have $160 left if both are approved.
>
> 103 (20 hoodies, size M, discount): Boss should call Inventory first, because there's no point discussing a discount on hoodies we don't have. I expect 8 in stock, 12 short, and the same blocked vendor. Then Accounting checks the margin (20% off is $46.40, still above the $22 cost) and whether we can afford restocking 12 ($264). We can't, since only $160 would be left, so I expect no purchase order. Then Customer Service drafts a conditional quote, maybe offering 8 now and 12 later. No Facilities. Tools: check_stock, list_inventory, check_vendor_status, get_pricing, check_margin, get_cash_balance, list_payment_requests, save_draft, update_ticket.
>
> Also note on the page that the tickets run in order 101, 102, 103, which is why 103 hits the cash problem. Write it the way I described it, keep it readable, and log this prompt in AI_prompts.md under Problem 6.

**Earlier prompts for this problem:** First I shared the problem and asked "Based on that give me suggestions for that", then "I love that. based on the talk with me give me a prompt to follow problem 6". The coder suggested a plan per ticket and a prompt, and I sent the prompt above with my plan.

**Follow-up prompts:**
> so you follow every instructions?

> follow everything I talked to you directly

**What was lacking after the first:** The coder flagged that the file name and wording differed from the assignment and that the page hadn't been tested in a browser. I told it to follow my direct instructions, so it kept my file name and wording and only tested that the tabs work.

---

## Problem 7: Backend routes

**Prompt:**
> Problem 7: Backend routes
>
> Your React fronend dashboard (the next problem) needs a backend it can call. In backed/main.py, use FastAPI and add routes that do the following:
>
> * Return the three tickets and wheter each is open or resolved
> * Tkae a ticket id and run your agent team on that ticket
> * Return recent agent events - what each agent said and which tools they used - so the board can refresh
> * Approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash)
> * Return the current checking balance from cash_accounts
> * Reset the database to the original values when you want to try a fresh run
>
> From the backend/ folder, start the server with:
> uvicorn main:app --reload --port 8000
>
> This turns on your backend at http://localhost:8000 so the frontend dashboard can call those routes
>
> In output/harness.md, list each route in one line (what URL / what it does).

**Follow-up prompt:** None needed. The coder wrote backend/main.py, tested every route on scratch copies of the database and audit log, and started the real server on port 8000.

---

## Problem 8: Agent dashboard

**Prompt:**
> Problem 8 : agent dashboard
>
> Build the frontend dashboard in frontend/ with React + Vite + TyptScript. The apge should call the routes you built in Problem 7. At minimum the board should:
>
> * List all three tickets
> * Let you pick one ticket and start the agent team on it
> * Show each agent and what they are saying / doing while the tickets runs
> * Mark a ticket resolved when the run finishes
> * Show a short summary of what each agent did on that ticket
> * Let a human approve a pay or purchase when asked
> * Show the checking balance (it shoud drop after an approved pay)
>
> Make the dashboard look good. Be creative with the layout and feel - this is a real desk people woud want to sit at, so put thought into how it looks.
>
> Tell the front end to talk to you backend at https://localhost:8000. On the backend, allow the Vite page origign(usually http://localhost:5173) so the browser is allowed to call those routes Start board with:
> npm run dev
>
> This opens the React desk in your browser so you can pick tickets and watch agents.
>
> Write output/design.md with what you chose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why - including the creative choices that make it feel special and something humans would actually enjoy using.

**Follow-up prompt:**
> before I submit, can you change the design with emphasis of Yale?

**What was lacking after the first:** The first look was a warm paper-and-cork desk that didn't say "Yale." The coder restyled it around Yale's identity: Yale Blue header with a shield mark and *Lux et Veritas*, a Yale-blue bulletin board, a Yale-blue till, agents in Yale's official secondary colours, and Handsome Dan touches. It also updated design.md and retook the resolved_board.html screenshots.

---

## Problem 9: Resolve the tickets

**Prompt:**
> Problem 9: Resolve the tickets
>
> Before testing the agents on a full run over the three tickets, reset the working database data/campus_custos_new.db again so you start clean. Note the starting chekcing balance. Then run all three tickets on the board (101, 102, 103) until each is resolved.
>
> Open output/dsek_tickets.html from Problem 6. On each ticket tab, fill the Actual section form this run: Which agent worked, what they delegated, and which tools they used. Kepp your expected section so you can compare the two.
>
> On the cahs tab of the same output/desk_tickets.html, itemize the money:
>
> * Starting chekcing balance (after the reset)
> * For each ticket: how each changed when that ticket resolved, and why (which pay/ purchase, dollar amount)
> * Ending checking balance - it must match cash_accounts in the working database
>
> Wrong cahs math loses points even if the board shows every ticket reolsved. Also save:
>
> * output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
> * output/resolved_board.html - a page you can double-click with a screenshot of your React board for each resolved ticket (101, 102, and 103)
>
> Appeal real runs to output/aduit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules

**Follow-up prompts:**
> *(screenshot of the dashboard's "Needs your signature" panel, signing as Youngjin Hahm)*

> I did *(with a screenshot of the board: all three tickets resolved, ledger showing #1 $840 and #2 $2,400 approved by Youngjin Hahm, till at $160.00)*

**What was lacking after the first:** The coder ran ticket 101 and then had to stop, because every payment needs a human signature. I reset the shop, ran 101 → 102 → 103 myself from the board, and signed both payments. Then the coder filled the Actual and Cash tabs, the JSON, the screenshot page, and the harness from the real data.

---

## Problem 10: Reflection

**Prompt:**
> Problem 10: Reflection
>
> Open output/desk_tickets.html and fill the Reflection tab.
>
> * How would you evaluate the performance of the agents on each ticket and why?
> * For each ticket, how did Actual compare to the Expected paln you wrote ealier?
> * What would have been simpler as one agent with tools - and why?
> * Describe three new problems Campus Customs might face that this agent team could sove with tools you built
> * Describe three new problems Campus Customs might face that this agent team could not sove with the tools you built, and explain the tools and agents you would need to solve them.
>
> Tie every answer to this app and the three tickets you ran - use the ticket tabs and cash tab on the same page as your eviendce.
>
> write this reflections in the perspective on the boss. and be concise. but should be reflect my on insight, especially as a person who are recruiting for Investment bank

**Follow-up prompts:**
> so did you follow everything I said?

> 1. make it more concise
> 2. show me insight I will make it in my languagr
>
> Tell me what I need to do

**What was lacking after the first:** The first reflection was about 750 words, not concise, and its takeaway was the coder's guess at my view. The coder cut it to about 380 words and marked the takeaway section for me to rewrite in my own words.

> 1. reflection : (영어로) 개선할 수 잇는 여지가 조금 더 있을 것 같다. 에이전트를 조금 더 분산하여서 기능을 하면 더 효율적으로 할 수 있ㅇ지 않으까 생각한다

**What this added:** I wrote my own takeaway in Korean, and the coder translated it into English and replaced its guessed takeaway with my words.

---

## Problem 11: Submit to GitHub

**Prompt:**
> *(screenshot of the expected file layout and the README requirements)*
>
> Problem 11: Submit to Github
>
> Push your code to a public GitHub repository so graders can clone it. Submit the repo URL to Canvas and also put it in output/github_url.txt
>
> Do not push your real .env to the GitHub repo. Do include both database files under data/ (the original and your working copy) so grader can run your app easily.
>
> Expected file layout: screen shot

**Follow-up prompt:** None needed. The coder matched the layout (added README.md and .env.example, renamed the audit file to output/audit_trail.json, embedded the screenshots in resolved_board.html), scanned the staged files for the real key, and pushed to https://github.com/youngjinhahm-yale/campus-customs-multi-agent.

---
