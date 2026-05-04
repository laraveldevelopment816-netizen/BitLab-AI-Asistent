import axios from 'axios'

// Dev: Vite proxy preusmjerava /api/* → http://localhost:8000.
// Prod: dashboard-dist se servira sa istog hosta kao API.
const http = axios.create({ baseURL: '/api/dashboard' })

// Bearer token iz localStorage. Settings stranica ga upisuje.
http.interceptors.request.use((config) => {
  const key = localStorage.getItem('bitlab.dashboardKey')
  if (key) config.headers.Authorization = `Bearer ${key}`
  return config
})

export interface ToolCall {
  iteration: number
  tool_name: string
  input_json: string
  output_text: string
  latency_ms: number
}

export interface RequestRow {
  id: number
  adapter: string
  channel: string
  model: string
  status: string
  tokens_in: number | null
  tokens_out: number | null
  latency_ms: number | null
  iterations: number | null
  cost_usd: number | null
  prompt_preview: string
  created_at: string
}

export interface RequestDetail extends Omit<RequestRow, 'prompt_preview'> {
  prompt: string
  response: string | null
  error: string | null
  compare_group_id: string | null
  tool_calls: ToolCall[]
}

export interface RequestsPage {
  items: RequestRow[]
  total: number
  page: number
  page_size: number
}

export interface RequestsFilter {
  adapter?: string
  channel?: string
  status?: string
  page?: number
}

export interface AdapterStats {
  adapter: string
  channel: string
  model: string
  total_requests: number
  ok_requests: number
  error_requests: number
  total_tokens_in: number
  total_tokens_out: number
  avg_latency_ms: number | null
  estimated_cost_usd: number
}

export interface StatsResponse {
  total_requests: number
  total_tokens_in: number
  total_tokens_out: number
  total_cost_usd: number
  by_adapter: AdapterStats[]
}

export interface CompareResultItem {
  model_key: string
  model: string
  request_id: number | null
  status: string
  reply: string
  tokens_in: number | null
  tokens_out: number | null
  latency_ms: number | null
  cost_usd: number | null
  error: string | null
  tool_calls: ToolCall[]
}

export interface CompareResponse {
  compare_group_id: string
  results: CompareResultItem[]
}

export interface SessionRow {
  session_id: string
  channel: string
  model: string
  msg_count: number
  first_message_at: string
  last_message_at: string
  total_tokens_in: number
  total_tokens_out: number
  total_latency_ms: number
  total_cost_usd: number | null
  error_count: number
  first_prompt_preview: string
}

export interface SessionsPage {
  items: SessionRow[]
  total: number
  page: number
  page_size: number
}

export interface SessionDetail {
  session_id: string
  requests: RequestDetail[]
}

export const api = {
  listRequests: (f: RequestsFilter = {}) =>
    http.get<RequestsPage>('/requests', { params: f }).then(r => r.data),

  getRequest: (id: number) =>
    http.get<RequestDetail>(`/requests/${id}`).then(r => r.data),

  getStats: () =>
    http.get<StatsResponse>('/stats').then(r => r.data),

  listErrors: (adapter?: string, page = 1) =>
    http.get<RequestsPage>('/errors', { params: { adapter, page } }).then(r => r.data),

  compare: (message: string, channel: string, models: string[]) =>
    http.post<CompareResponse>('/compare', { message, channel, models })
        .then(r => r.data),

  listSessions: (channel?: string, page = 1) =>
    http.get<SessionsPage>('/sessions', { params: { channel, page } }).then(r => r.data),

  getSession: (sessionId: string) =>
    http.get<SessionDetail>(`/sessions/${sessionId}`).then(r => r.data),
}
