import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { agentStates } from './agents'
import { API_BASE, api } from './api'
import { AgentRoster } from './components/AgentRoster'
import { ApprovalInbox } from './components/ApprovalInbox'
import { CashTill } from './components/CashTill'
import { LiveFloor } from './components/LiveFloor'
import { Outbox } from './components/Outbox'
import { ShiftReport } from './components/ShiftReport'
import { TicketBoard } from './components/TicketBoard'
import { money } from './format'
import type { AgentEvent, Cash, Draft, PaymentRequest, Ticket } from './types'

interface Toast { id: number; text: string; tone: 'ok' | 'bad' | 'info' }

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  // ?ticket=101 opens the desk on that ticket (handy for links and screenshots).
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const id = Number(new URLSearchParams(window.location.search).get('ticket'))
    return Number.isInteger(id) && id > 0 ? id : null
  })
  const [runningId, setRunningId] = useState<number | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [requests, setRequests] = useState<PaymentRequest[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [online, setOnline] = useState<boolean | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [approver, setApproverState] = useState(() => localStorage.getItem('approver') ?? '')
  const cursor = useRef(0)

  const toast = useCallback((text: string, tone: Toast['tone'] = 'info') => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, text, tone }])
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5200)
  }, [])

  const setApprover = (name: string) => {
    setApproverState(name)
    localStorage.setItem('approver', name)
  }

  // --- data loading ---------------------------------------------------------

  const refreshDesk = useCallback(async () => {
    try {
      const [t, c, r, d] = await Promise.all([api.tickets(), api.cash(), api.paymentRequests(), api.drafts()])
      setTickets(t)
      setCash(c)
      setRequests(r)
      setDrafts(d)
      setOnline(true)
      setSelectedId((cur) => cur ?? t[0]?.id ?? null)
      const live = t.find((x) => x.run?.status === 'running')
      setRunningId(live ? live.id : null)
    } catch {
      setOnline(false)
    }
  }, [])

  const loadEvents = useCallback(async (ticketId: number, fresh: boolean) => {
    try {
      const page = await api.events(ticketId, fresh ? 0 : cursor.current)
      cursor.current = page.next_after
      setEvents((prev) => (fresh ? page.events : [...prev, ...page.events]))
    } catch { /* shown by the offline badge */ }
  }, [])

  useEffect(() => { refreshDesk() }, [refreshDesk])

  useEffect(() => {
    if (selectedId == null) return
    loadEvents(selectedId, true)
  }, [selectedId, loadEvents])

  // Slow heartbeat for the whole desk; fast polling while the team is working.
  useEffect(() => {
    const id = window.setInterval(refreshDesk, runningId ? 2000 : 6000)
    return () => window.clearInterval(id)
  }, [refreshDesk, runningId])

  useEffect(() => {
    if (runningId == null || selectedId == null) return
    const id = window.setInterval(() => loadEvents(selectedId, false), 1200)
    return () => window.clearInterval(id)
  }, [runningId, selectedId, loadEvents])

  // Announce when a run finishes.
  const lastRunning = useRef<number | null>(null)
  useEffect(() => {
    if (lastRunning.current != null && runningId == null) {
      const done = tickets.find((t) => t.id === lastRunning.current)
      if (done?.run?.status === 'done') toast(`Ticket #${done.id} resolved — see the shift report.`, 'ok')
      else if (done?.run?.error) toast(`Ticket #${done.id}: ${done.run.error}`, 'bad')
      if (selectedId != null) loadEvents(selectedId, false)
    }
    lastRunning.current = runningId
  }, [runningId, tickets, selectedId, loadEvents, toast])

  // --- actions --------------------------------------------------------------

  const run = async (id: number) => {
    try {
      setSelectedId(id)
      await api.runTicket(id)
      setRunningId(id)
      toast(`The team picked up ticket #${id}.`, 'info')
      refreshDesk()
    } catch (e) {
      toast((e as Error).message, 'bad')
    }
  }

  const approve = async (id: number) => {
    try {
      const res = await api.approve(id, approver.trim())
      toast(`Paid. Checking is now ${money(res.new_balance)}.`, 'ok')
    } catch (e) {
      toast(`Not paid: ${(e as Error).message}`, 'bad')
    }
    refreshDesk()
  }

  const reject = async (id: number) => {
    const reason = window.prompt('Why are you rejecting this request?')
    if (!reason) return
    try {
      await api.reject(id, approver.trim(), reason)
      toast(`Request #${id} rejected.`, 'info')
    } catch (e) {
      toast((e as Error).message, 'bad')
    }
    refreshDesk()
  }

  const reset = async () => {
    if (!window.confirm('Reset the shop database to the original values? Pending requests, drafts and ticket updates will be cleared. The audit trail is kept.')) return
    try {
      await api.reset()
      toast('Fresh start: database reset to the original.', 'ok')
      await refreshDesk()
      if (selectedId != null) loadEvents(selectedId, true)
    } catch (e) {
      toast((e as Error).message, 'bad')
    }
  }

  // --- derived --------------------------------------------------------------

  const selected = tickets.find((t) => t.id === selectedId) ?? null
  const running = runningId != null && runningId === selectedId
  const runEvents = useMemo(() => {
    const starts = events.filter((e) => e.event === 'run_start')
    const last = starts[starts.length - 1]
    return last ? events.filter((e) => e.run_id === last.run_id) : []
  }, [events])
  const states = useMemo(() => agentStates(runEvents, running), [runEvents, running])
  const pending = requests.filter((r) => r.status === 'pending')
  const runFinished = runEvents.some((e) => e.event === 'run_end')

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden><span>CC</span></span>
          <div>
            <p className="motto">Lux et Veritas · New Haven, Connecticut</p>
            <h1>Campus Customs <em>Back Office</em></h1>
            <p>Five agents, one till, and you holding the pen.</p>
          </div>
        </div>
        <div className="topbar-right">
          <span className={`conn ${online ? 'on' : online === false ? 'off' : ''}`}>
            <i /> {online ? 'Backend connected' : online === false ? `Backend offline (${API_BASE})` : 'Connecting…'}
          </span>
          <button className="ghost" onClick={reset} disabled={runningId != null}>↺ Reset shop</button>
        </div>
      </header>

      <main className="layout">
        <TicketBoard
          tickets={tickets}
          selectedId={selectedId}
          runningId={runningId}
          pending={pending}
          onSelect={setSelectedId}
          onRun={run}
        />

        <section className="panel stage">
          <header className="panel-head">
            <h2>{selected ? <>The Floor <span className="stage-ticket">· #{selected.id} {selected.subject}</span></> : 'The Floor'}</h2>
            {running && <span className="live-badge"><i className="dot" /> LIVE</span>}
          </header>
          <AgentRoster states={states} />
          <LiveFloor events={runEvents} running={running} />
          {runFinished && <ShiftReport events={runEvents} />}
        </section>

        <aside className="side">
          <CashTill cash={cash} />
          <ApprovalInbox
            requests={requests}
            approver={approver}
            setApprover={setApprover}
            onApprove={approve}
            onReject={reject}
          />
          <Outbox drafts={drafts} />
        </aside>
      </main>

      <footer className="footer">
        <span>🐶 Handsome Dan approves of human sign-off.</span>
        <span className="footer-motto">Lux et Veritas</span>
        <span>Campus Customs · Chapel Street, New Haven</span>
      </footer>

      <div className="toasts">
        {toasts.map((t) => <div key={t.id} className={`toast ${t.tone}`}>{t.text}</div>)}
      </div>
    </div>
  )
}
