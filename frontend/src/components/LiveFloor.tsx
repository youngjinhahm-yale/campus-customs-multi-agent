import { useEffect, useRef } from 'react'
import { AGENTS } from '../agents'
import { clock, formatCall, gist } from '../format'
import type { AgentEvent, AgentName, AgentReport, TicketResolution } from '../types'

interface Props {
  events: AgentEvent[]
  running: boolean
}

const HIDDEN_CALLS = new Set(['final_result', 'delegate_to_agent'])

/** The live transcript: every agent's words and tool calls, threaded by delegation depth. */
export function LiveFloor({ events, running }: Props) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (running) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [events.length, running])

  if (events.length === 0) {
    return (
      <div className="floor empty">
        <p className="empty-big">The floor is quiet. Handsome Dan is napping. 🐶</p>
        <p>Pick a ticket on the board and press <b>Start the team</b> to watch the agents work it.</p>
      </div>
    )
  }

  return (
    <div className="floor">
      {events.map((e) => <Line key={e.index} e={e} />)}
      {running && (
        <div className="typing"><span /><span /><span /></div>
      )}
      <div ref={endRef} />
    </div>
  )
}

function Line({ e }: { e: AgentEvent }) {
  const agent = e.agent ? AGENTS[e.agent] : null
  const style = { '--agent': agent?.color ?? '#555', '--depth': e.depth } as React.CSSProperties
  const nest = e.depth > 0 ? " nested" : ""

  switch (e.event) {
    case 'run_start':
      return <div className="divider"><span>Run started · {clock(e.ts)}</span></div>

    case 'user_prompt':
      if (e.depth > 0) return null
      return (
        <div className={`line system${nest}`} style={style}>
          <span className="who">📥 Ticket handed to the Boss</span>
        </div>
      )

    case 'delegation_start': {
      const to = AGENTS[e.detail.to as AgentName]
      return (
        <div className={`line handoff${nest}`} style={style}>
          <div className="handoff-head">
            <span className="chip" style={{ background: agent?.color }}>{agent?.icon} {agent?.name}</span>
            <span className="arrow">→</span>
            <span className="chip" style={{ background: to?.color }}>{to?.icon} {to?.name}</span>
            <time>{clock(e.ts)}</time>
          </div>
          <p className="handoff-task">“{String(e.detail.task)}”</p>
        </div>
      )
    }

    case 'delegation_refused':
      return (
        <div className={`line warn${nest}`} style={style}>
          ⚠️ {agent?.name} tried to hand off to {String(e.detail.to)}: {String(e.detail.reason)}
        </div>
      )

    case 'model_response': {
      const calls = e.tool_calls.filter((c) => !HIDDEN_CALLS.has(c.tool))
      if (!e.said && calls.length === 0) return null
      return (
        <div className={`line speech${nest}`} style={style}>
          <Avatar name={e.agent} />
          <div className="bubble">
            <div className="bubble-head"><b>{agent?.name}</b><time>{clock(e.ts)}</time></div>
            {e.said && <p>{e.said}</p>}
            {calls.map((c, i) => (
              <code key={i} className="call">⚙ {formatCall(c.tool, c.args)}</code>
            ))}
          </div>
        </div>
      )
    }

    case 'model_request': {
      const results = e.tool_results.filter((r) => r.tool && !HIDDEN_CALLS.has(r.tool))
      if (results.length === 0) return null
      return (
        <div className={`line results${nest}`} style={style}>
          {results.map((r, i) => (
            <div key={i} className="result">↳ <b>{r.tool}</b> {gist(r.content)}</div>
          ))}
        </div>
      )
    }

    case 'final_output': {
      const out = e.detail.output as AgentReport | TicketResolution
      const text = 'decision' in out ? out.decision : out.summary
      return (
        <div className={`line report${nest}`} style={style}>
          <Avatar name={e.agent} />
          <div className="bubble report-bubble">
            <div className="bubble-head">
              <b>{agent?.name}</b> <span className="tag">{'decision' in out ? 'Final call' : 'Report'}</span>
              <time>{clock(e.ts)}</time>
            </div>
            <p>{text}</p>
          </div>
        </div>
      )
    }

    case 'error':
      return <div className={`line warn${nest}`}>⛔ {String(e.detail.type)}: {String(e.detail.message)}</div>

    case 'run_end':
      return <div className="divider done"><span>Run finished · {clock(e.ts)}</span></div>

    default:
      return null
  }
}

function Avatar({ name }: { name: AgentName | null }) {
  const a = name ? AGENTS[name] : null
  return <div className="avatar" style={{ background: a?.color }} title={a?.name}>{a?.icon}</div>
}
