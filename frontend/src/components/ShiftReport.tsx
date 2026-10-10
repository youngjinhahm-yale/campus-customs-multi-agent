import { AGENTS, AGENT_ORDER } from '../agents'
import type { AgentEvent, AgentName, AgentReport, TicketResolution } from '../types'

interface Props {
  events: AgentEvent[]
}

/** After a run: one card per agent that worked the ticket - what they did, which tools. */
export function ShiftReport({ events }: Props) {
  const reports = new Map<AgentName, AgentReport | TicketResolution>()
  const tools = new Map<AgentName, Map<string, number>>()
  for (const e of events) {
    if (!e.agent) continue
    if (e.event === 'final_output') reports.set(e.agent, e.detail.output as AgentReport | TicketResolution)
    if (e.event === 'model_response') {
      const m = tools.get(e.agent) ?? new Map<string, number>()
      for (const c of e.tool_calls) {
        if (c.tool === 'final_result') continue
        m.set(c.tool, (m.get(c.tool) ?? 0) + 1)
      }
      tools.set(e.agent, m)
    }
  }
  const lastUsage = [...events].reverse().find((e) => e.usage)?.usage
  const boss = reports.get('boss') as TicketResolution | undefined
  const crew = AGENT_ORDER.filter((a) => a !== 'boss' && reports.has(a))
  const benched = AGENT_ORDER.filter((a) => a !== 'boss' && !reports.has(a))

  if (!boss && crew.length === 0) return null

  return (
    <section className="shift">
      <header className="shift-head">
        <h3>Shift report</h3>
        {lastUsage && (
          <span className="panel-sub">
            {lastUsage.requests} model calls · {lastUsage.tool_calls} tool calls · {lastUsage.total_tokens?.toLocaleString()} tokens
          </span>
        )}
      </header>

      {boss && (
        <div className="boss-call" style={{ '--agent': AGENTS.boss.color } as React.CSSProperties}>
          <div className="boss-call-head">🧭 The Boss's call <span className="tag">{boss.final_status.replace('_', ' ')}</span></div>
          <p>{boss.decision}</p>
          {boss.next_steps_for_human.length > 0 && (
            <>
              <h4>For you</h4>
              <ol>{boss.next_steps_for_human.map((s, i) => <li key={i}>{s}</li>)}</ol>
            </>
          )}
        </div>
      )}

      <div className="crew">
        {crew.map((a) => {
          const r = reports.get(a) as AgentReport
          const used = [...(tools.get(a) ?? new Map()).entries()]
          return (
            <div key={a} className="crew-card" style={{ '--agent': AGENTS[a].color } as React.CSSProperties}>
              <div className="crew-head">{AGENTS[a].icon} <b>{AGENTS[a].name}</b></div>
              <p>{r.summary}</p>
              {r.blockers.length > 0 && <p className="blockers">⚠️ {r.blockers.join(' · ')}</p>}
              <div className="crew-tools">
                {used.map(([t, n]) => <span key={t}>{t}{n > 1 ? ` ×${n}` : ''}</span>)}
              </div>
              {(r.payment_request_ids.length > 0 || r.draft_ids.length > 0) && (
                <div className="crew-out">
                  {r.payment_request_ids.map((id) => <span key={`p${id}`}>💵 request #{id}</span>)}
                  {r.draft_ids.map((id) => <span key={`d${id}`}>✉️ draft #{id}</span>)}
                </div>
              )}
            </div>
          )
        })}
      </div>
      {benched.length > 0 && (
        <p className="benched">Not needed on this ticket: {benched.map((a) => AGENTS[a].name).join(', ')}</p>
      )}
    </section>
  )
}
