import { AGENTS, AGENT_ORDER, describeState, type AgentState } from '../agents'
import type { AgentName } from '../types'

interface Props {
  states: Record<AgentName, AgentState>
}

/** Five desks in a row: who's working, who's waiting on whom, who's done. */
export function AgentRoster({ states }: Props) {
  return (
    <div className="roster">
      {AGENT_ORDER.map((key) => {
        const a = AGENTS[key]
        const s = states[key]
        return (
          <div key={key} className={`desk state-${s.kind}`} style={{ '--agent': a.color } as React.CSSProperties}>
            <div className="desk-avatar">{a.icon}</div>
            <div className="desk-text">
              <strong>{a.name}</strong>
              <span>{describeState(s)}</span>
            </div>
            <i className="desk-light" />
          </div>
        )
      })}
    </div>
  )
}
