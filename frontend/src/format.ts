export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const clock = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit' })

export function shopDate(iso: string | undefined): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  })
}

function short(v: unknown, max = 40): string {
  const s = typeof v === 'string' ? JSON.stringify(v) : JSON.stringify(v) ?? String(v)
  return s.length > max ? s.slice(0, max - 1) + '…' : s
}

/** check_stock(sku: "CC-TEE-WHITE", size: "S", qty_needed: 1) */
export function formatCall(tool: string, args: Record<string, unknown>): string {
  const parts = Object.entries(args)
    .filter(([k]) => !['requested_by', 'author', 'updated_by', 'reason', 'body'].includes(k))
    .map(([k, v]) => `${k}: ${short(v, 28)}`)
  return `${tool}(${parts.join(', ')})`
}

/** A one-line gist of a tool's return value. */
export function gist(content: unknown): string {
  let value = content
  if (typeof value === 'string') {
    try { value = JSON.parse(value) } catch { return short(value, 120) }
  }
  if (Array.isArray(value)) return `${value.length} row${value.length === 1 ? '' : 's'}`
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>
    if ('result' in obj && Object.keys(obj).length === 1) return gist(obj.result)
    const preferred = ['message', 'qty_on_hand', 'shortfall', 'will_ship', 'lead_days', 'open_balance',
      'balance', 'amount', 'monthly_rent', 'next_due', 'days_until_due', 'margin_pct', 'request_id',
      'draft_id', 'status', 'paid']
    const keys = preferred.filter((k) => k in obj).slice(0, 4)
    const use = keys.length ? keys : Object.keys(obj).slice(0, 3)
    return use.map((k) => `${k}=${short(obj[k], 24)}`).join(' · ')
  }
  return short(value, 120)
}
