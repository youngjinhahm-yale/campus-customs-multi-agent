import { useEffect, useRef, useState } from 'react'
import { money, shopDate } from '../format'
import type { Cash } from '../types'

/** The till: a register-style balance that counts down when a payment clears. */
export function CashTill({ cash }: { cash: Cash | null }) {
  const target = cash?.balance ?? 0
  const [shown, setShown] = useState(target)
  const [drop, setDrop] = useState<number | null>(null)
  const prev = useRef<number | null>(null)

  useEffect(() => {
    if (cash == null) return
    const from = prev.current ?? target
    prev.current = target
    if (from === target) { setShown(target); return }
    if (target < from) {
      setDrop(from - target)
      window.setTimeout(() => setDrop(null), 2600)
    }
    const start = performance.now()
    let raf = 0
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / 900)
      const eased = 1 - Math.pow(1 - k, 3)
      setShown(from + (target - from) * eased)
      if (k < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, cash])

  const pending = cash?.pending_requests_total ?? 0
  const projected = cash?.projected_balance_if_all_approved ?? 0
  const pendingPct = cash && cash.balance > 0 ? Math.min(100, (pending / cash.balance) * 100) : 0

  return (
    <section className="till">
      <div className="till-label">
        <span>Checking</span>
        <span>{shopDate(cash?.date)}</span>
      </div>
      <div className="till-display">
        <span className="till-amount">{money(shown)}</span>
        {drop != null && <span className="till-drop">−{money(drop)}</span>}
      </div>
      <div className="till-bar" title="Share of the balance already claimed by pending requests">
        <div className={`till-bar-fill ${projected < 0 ? 'over' : ''}`} style={{ width: `${pendingPct}%` }} />
      </div>
      <div className="till-foot">
        <span>Waiting to sign <b>{money(pending)}</b></span>
        <span className={projected < 0 ? 'neg' : ''}>If all signed <b>{money(projected)}</b></span>
      </div>
      <p className="till-note">Cash only goes out here — no revenue is modeled. The till refuses anything that would go below $0.</p>
    </section>
  )
}
