export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface RunStatus {
  ticket_id: number
  status: 'running' | 'done' | 'stopped' | 'error'
  started_at: string
  finished_at: string | null
  resolution: TicketResolution | null
  boss_outcome?: string
  error: string | null
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  state: 'open' | 'resolved'
  run: RunStatus | null
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
}

export interface ToolResult {
  tool: string | null
  content: unknown
}

export interface Usage {
  requests: number | null
  tool_calls: number | null
  total_tokens: number | null
}

export interface AgentEvent {
  index: number
  ts: string
  run_id: string
  ticket_id: number | null
  agent: AgentName | null
  depth: number
  step: number | null
  event: string
  said: string | null
  tool_calls: ToolCall[]
  tool_results: ToolResult[]
  usage: Usage | null
  detail: Record<string, unknown>
}

export interface EventsPage {
  total: number
  next_after: number
  events: AgentEvent[]
}

export interface Fact {
  label: string
  value: string
  source_tool: string
}

export interface AgentReport {
  agent: AgentName
  ticket_id: number
  summary: string
  facts: Fact[]
  actions_taken: string[]
  payment_request_ids: number[]
  draft_ids: number[]
  blockers: string[]
  recommendation: string
}

export interface TicketResolution {
  ticket_id: number
  final_status: string
  decision: string
  agents_consulted: AgentName[]
  payment_request_ids: number[]
  draft_ids: number[]
  next_steps_for_human: string[]
  summary: string
}

export interface PaymentRequest {
  id: number
  ticket_id: number | null
  kind: 'invoice' | 'rent' | 'purchase_order'
  ref_id: number | null
  vendor_id: number | null
  sku: string | null
  size: string | null
  qty: number | null
  amount: number
  account: string
  reason: string | null
  requested_by: string
  status: 'pending' | 'approved' | 'rejected' | 'refused'
  created_at: string
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
  payment_id: number | null
}

export interface Cash {
  found: boolean
  name: string
  balance: number
  date: string
  pending_requests_total: number
  projected_balance_if_all_approved: number
}

export interface Draft {
  id: number
  ticket_id: number | null
  kind: string
  recipient: string
  subject: string
  body: string
  author: string
  created_at: string
}
