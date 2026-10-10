import { useState } from 'react'
import { AGENTS } from '../agents'
import { money } from '../format'
import type { AgentName, PaymentRequest } from '../types'

const KIND: Record<PaymentRequest['kind'], string> = {
  invoice: 'Vendor invoice',
  rent: 'Rent',
  purchase_order: 'Purchase order',
}

interface Props {
  requests: PaymentRequest[]
  approver: string
  setApprover: (name: string) => void
  onApprove: (id: number) => Promise<void>
  onReject: (id: number) => Promise<void>
}

/** "Needs your signature": each request is a voucher only a human can sign. */
export function ApprovalInbox({ requests, approver, setApprover, onApprove, onReject }: Props) {
  const [busy, setBusy] = useState<number | null>(null)
  const pending = requests.filter((r) => r.status === 'pending')
  const decided = requests.filter((r) => r.status !== 'pending').slice(-4).reverse()

  const act = async (id: number, fn: (id: number) => Promise<void>) => {
    setBusy(id)
    try { await fn(id) } finally { setBusy(null) }
  }

  return (
    <section className="panel inbox">
      <header className="panel-head">
        <h2>Needs your signature</h2>
        <span className="panel-sub">{pending.length} waiting</span>
      </header>

      <label className="signer">
        <span>Signing as</span>
        <input
          value={approver}
          placeholder="Your name"
          onChange={(e) => setApprover(e.target.value)}
        />
      </label>

      {pending.length === 0 && <p className="muted">Nothing to sign. Agents can only prepare payments — they land here for you.</p>}

      {pending.map((r) => {
        const by = AGENTS[r.requested_by as AgentName]
        return (
          <div key={r.id} className="voucher">
            <div className="voucher-top">
              <span className="voucher-kind">{KIND[r.kind]}</span>
              <span className="voucher-no">No. {String(r.id).padStart(4, '0')}</span>
            </div>
            <div className="voucher-amount">{money(r.amount)}</div>
            <div className="voucher-meta">
              {r.kind === 'invoice' && <span>Invoice #{r.ref_id}</span>}
              {r.kind === 'rent' && <span>Lease #{r.ref_id}</span>}
              {r.kind === 'purchase_order' && <span>{r.qty} × {r.sku} {r.size}</span>}
              {r.ticket_id && <span>Ticket #{r.ticket_id}</span>}
              <span>Prepared by {by ? `${by.icon} ${by.name}` : r.requested_by}</span>
            </div>
            {r.reason && <p className="voucher-reason">{r.reason}</p>}
            <div className="voucher-actions">
              <button
                className="approve"
                disabled={!approver.trim() || busy === r.id}
                onClick={() => act(r.id, onApprove)}
                title={approver.trim() ? '' : 'Type your name first'}
              >
                {busy === r.id ? 'Signing…' : 'Approve & pay'}
              </button>
              <button
                className="reject"
                disabled={!approver.trim() || busy === r.id}
                onClick={() => act(r.id, onReject)}
              >
                Reject
              </button>
            </div>
          </div>
        )
      })}

      {decided.length > 0 && (
        <div className="ledger">
          <h4>Ledger</h4>
          {decided.map((r) => (
            <div key={r.id} className={`ledger-row ${r.status}`}>
              <span>#{r.id} {KIND[r.kind]}</span>
              <span>{money(r.amount)}</span>
              <span className="ledger-status" title={r.decision_note ?? ''}>
                {r.status}{r.decided_by ? ` · ${r.decided_by}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
