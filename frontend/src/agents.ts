import type { AgentEvent, AgentName } from './types'

export interface AgentMeta {
  key: AgentName
  name: string
  role: string
  icon: string
  color: string
}

// Each agent has its own colour, glyph, and voice line so you can tell who is
// talking at a glance - like nameplates on desks. Colours come from Yale's
// official palette: Yale Blue plus the secondary blue, green, orange and grey.
export const AGENTS: Record<AgentName, AgentMeta> = {
  boss: { key: 'boss', name: 'Boss', role: 'Routes tickets · makes the call', icon: '🧭', color: '#00356b' },
  inventory: { key: 'inventory', name: 'Inventory', role: 'Stock · sizes · vendors', icon: '📦', color: '#5f712d' },
  accounting: { key: 'accounting', name: 'Accounting', role: 'Cash · invoices · margins', icon: '🧾', color: '#bd5319' },
  facilities: { key: 'facilities', name: 'Facilities', role: 'Lease · rent · landlord', icon: '🏛️', color: '#7a6f66' },
  customer_service: { key: 'customer_service', name: 'Customer Service', role: 'Drafts customer replies', icon: '💬', color: '#286dc0' },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export type AgentState =
  | { kind: 'idle' }
  | { kind: 'thinking' }
  | { kind: 'tool'; tool: string }
  | { kind: 'waiting'; on: AgentName }
  | { kind: 'done' }

/** Work out what every agent is doing right now from the run's events. */
export function agentStates(events: AgentEvent[], running: boolean): Record<AgentName, AgentState> {
  const states = Object.fromEntries(AGENT_ORDER.map((a) => [a, { kind: 'idle' }])) as Record<AgentName, AgentState>
  for (const e of events) {
    if (!e.agent) continue
    switch (e.event) {
      case 'user_prompt':
      case 'model_request':
        states[e.agent] = { kind: 'thinking' }
        break
      case 'model_response': {
        const tool = e.tool_calls.find((c) => c.tool !== 'final_result')
        states[e.agent] = tool ? { kind: 'tool', tool: tool.tool } : { kind: 'thinking' }
        break
      }
      case 'delegation_start':
        states[e.agent] = { kind: 'waiting', on: e.detail.to as AgentName }
        break
      case 'delegation_end':
        states[e.agent] = { kind: 'thinking' }
        break
      case 'final_output':
        states[e.agent] = { kind: 'done' }
        break
    }
  }
  if (!running) {
    for (const a of AGENT_ORDER) if (states[a].kind !== 'idle') states[a] = { kind: 'done' }
  }
  return states
}

export function describeState(s: AgentState): string {
  switch (s.kind) {
    case 'idle': return 'Not on this ticket'
    case 'thinking': return 'Thinking…'
    case 'tool': return `Using ${s.tool}`
    case 'waiting': return `Waiting on ${AGENTS[s.on]?.name ?? s.on}`
    case 'done': return 'Done'
  }
}
