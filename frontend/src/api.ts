import type { Cash, Draft, EventsPage, PaymentRequest, RunStatus, Ticket } from './types'

// The FastAPI backend from Problem 7 (backend/main.py). It allows this page's
// origin (http://localhost:5173) through CORS.
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function messageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      return String((detail as { message: unknown }).message)
    }
  }
  return fallback
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(API_BASE + path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_BASE}. Is uvicorn running?`)
  }
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, messageFrom(body, `${res.status} ${res.statusText}`))
  return body as T
}

export const api = {
  health: () => request<{ ok: boolean; model: string }>('/api/health'),
  tickets: () => request<Ticket[]>('/api/tickets'),
  runTicket: (id: number) => request<RunStatus>(`/api/tickets/${id}/run`, { method: 'POST' }),
  runStatus: (id: number) => request<RunStatus>(`/api/tickets/${id}/run`),
  events: (ticketId: number, after = 0) =>
    request<EventsPage>(`/api/events?ticket_id=${ticketId}&after=${after}&limit=1000`),
  paymentRequests: () => request<PaymentRequest[]>('/api/payment-requests'),
  approve: (id: number, approvedBy: string) =>
    request<{ paid: boolean; new_balance: number }>(`/api/payment-requests/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  reject: (id: number, decidedBy: string, reason: string) =>
    request<{ rejected: boolean }>(`/api/payment-requests/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ decided_by: decidedBy, reason }),
    }),
  cash: () => request<Cash>('/api/cash'),
  drafts: () => request<Draft[]>('/api/drafts'),
  reset: () => request<{ reset: boolean }>('/api/reset', { method: 'POST' }),
}
