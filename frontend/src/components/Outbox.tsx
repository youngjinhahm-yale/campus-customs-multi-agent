import { AGENTS } from '../agents'
import type { AgentName, Draft } from '../types'

/** Drafts the agents wrote. They stay here - nothing is ever sent. */
export function Outbox({ drafts }: { drafts: Draft[] }) {
  if (drafts.length === 0) return null
  return (
    <section className="panel outbox">
      <header className="panel-head">
        <h2>Outbox</h2>
        <span className="panel-sub">drafts · never sent</span>
      </header>
      {drafts.map((d) => {
        const a = AGENTS[d.author as AgentName]
        return (
          <details key={d.id} className="letter">
            <summary>
              <span className="letter-to">To {d.recipient}</span>
              <span className="letter-subject">{d.subject}</span>
              <span className="letter-by">{a?.icon} #{d.ticket_id}</span>
            </summary>
            <p>{d.body}</p>
            <span className="unsent">DRAFT · NOT SENT</span>
          </details>
        )
      })}
    </section>
  )
}
