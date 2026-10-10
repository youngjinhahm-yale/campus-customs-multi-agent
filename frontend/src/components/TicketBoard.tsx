import type { PaymentRequest, Ticket } from '../types'

const TYPE_LABEL: Record<string, { label: string; icon: string }> = {
  customer_order: { label: 'Customer order', icon: '🛍️' },
  rent_notice: { label: 'Rent notice', icon: '🏠' },
  price_override: { label: 'Discount request', icon: '🏷️' },
}

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  runningId: number | null
  pending: PaymentRequest[]
  onSelect: (id: number) => void
  onRun: (id: number) => void
}

export function TicketBoard({ tickets, selectedId, runningId, pending, onSelect, onRun }: Props) {
  return (
    <section className="panel board">
      <header className="panel-head">
        <h2>The Board</h2>
        <span className="panel-sub">{tickets.filter((t) => t.state === 'open').length} open</span>
      </header>
      <div className="cards">
        {tickets.map((t, i) => {
          const type = TYPE_LABEL[t.type] ?? { label: t.type, icon: '📌' }
          const running = runningId === t.id
          const waiting = pending.filter((p) => p.ticket_id === t.id).length
          return (
            <article
              key={t.id}
              className={`card tilt-${i % 3} ${selectedId === t.id ? 'selected' : ''} ${t.state}`}
              onClick={() => onSelect(t.id)}
            >
              <span className="pin" aria-hidden />
              <div className="card-top">
                <span className="card-type">{type.icon} {type.label}</span>
                <span className="card-id">#{t.id}</span>
              </div>
              <h3>{t.subject}</h3>
              <p className="card-from">from {t.requester}</p>
              <p className="card-note">{t.notes?.split('\n')[0]}</p>
              {(t.sku || t.lease_id) && (
                <div className="card-tags">
                  {t.sku && <span>{t.sku}</span>}
                  {t.size && <span>size {t.size}</span>}
                  {t.qty != null && <span>qty {t.qty}</span>}
                  {t.lease_id && <span>lease {t.lease_id}</span>}
                  {t.invoice_id && <span>invoice {t.invoice_id}</span>}
                </div>
              )}
              <div className="card-foot">
                {running ? (
                  <span className="status-chip live"><i className="dot" /> Team at work</span>
                ) : (
                  <span className={`status-chip ${t.state}`}>{t.status.replace('_', ' ')}</span>
                )}
                {waiting > 0 && <span className="status-chip sign">✍️ {waiting} to sign</span>}
              </div>
              <button
                className="run-btn"
                disabled={runningId !== null}
                onClick={(e) => { e.stopPropagation(); onRun(t.id) }}
              >
                {running ? 'Running…' : t.state === 'resolved' ? 'Run again' : 'Start the team →'}
              </button>
              {t.state === 'resolved' && !running && <div className="stamp">Resolved</div>}
            </article>
          )
        })}
      </div>
      <p className="board-hint">Tip: run them in order — 101, 102, 103 — they share one checking account.</p>
    </section>
  )
}
