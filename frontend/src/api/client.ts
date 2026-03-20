const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export type AuthPayload = {
  token: string
  user: {
    id: number
    username: string
    created_at: string
  }
}

export type SessionSummary = {
  id: string
  title: string
  category: string
  created_at: string
  updated_at: string
  last_message_preview: string
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export type SourceRecord = {
  source_name: string
  provider: string
  source_url: string
  notes: string
}

export type Product = {
  id: string
  title: string
  brand: string
  platform: string
  price: number
  image_url: string
  product_url: string
  source_count: number
  matched_keywords: string[]
  score: number
  category: string
  highlights: string[]
  dynamic_facets: Record<string, string[]>
  source_records: SourceRecord[]
}

export type FacetDefinition = {
  key: string
  label: string
  type: 'enum' | 'range' | 'tag'
  chart: 'bar' | 'pie' | 'list'
  options: Array<{ value: string; count: number }>
}

export type SessionFacets = {
  category: string
  fixed: FacetDefinition[]
  dynamic: FacetDefinition[]
}

export type SessionStats = {
  session_id: string
  total_products: number
  average_price: number
  chart_groups: Record<string, Array<{ label: string; value: number }>>
}

type RequestOptions = RequestInit & {
  token?: string | null
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`)
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || 'Request failed')
  }
  return response.json() as Promise<T>
}

export const authApi = {
  register: (payload: { username: string; password: string }) =>
    request<AuthPayload>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload: { username: string; password: string }) =>
    request<AuthPayload>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  me: (token: string) => request<AuthPayload['user']>('/auth/me', { token })
}

export const chatApi = {
  listSessions: (token: string) => request<SessionSummary[]>('/chat/sessions', { token }),
  createSession: (token: string, title?: string) =>
    request<SessionSummary>('/chat/sessions', { method: 'POST', token, body: JSON.stringify({ title }) }),
  listMessages: (token: string, sessionId: string) =>
    request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`, { token }),
  listProducts: (token: string, sessionId: string) =>
    request<Product[]>(`/chat/sessions/${sessionId}/products`, { token }),
  listFacets: (token: string, sessionId: string) =>
    request<SessionFacets>(`/chat/sessions/${sessionId}/facets`, { token }),
  listStats: (token: string, sessionId: string) =>
    request<SessionStats>(`/products/stats?session_id=${sessionId}`, { token })
}

export type StreamHandlers = {
  onStatus?: (payload: any) => void
  onPlan?: (payload: any) => void
  onToken?: (payload: any) => void
  onProducts?: (payload: any) => void
  onDone?: (payload: any) => void
}

function dispatchEvent(type: string, payload: any, handlers: StreamHandlers) {
  if (type === 'status') handlers.onStatus?.(payload)
  if (type === 'plan') handlers.onPlan?.(payload)
  if (type === 'token') handlers.onToken?.(payload)
  if (type === 'products') handlers.onProducts?.(payload)
  if (type === 'done') handlers.onDone?.(payload)
}

function parseSseBlock(block: string, handlers: StreamHandlers) {
  const lines = block.split('\n')
  let eventName = 'message'
  let data = ''
  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      data += line.slice(5).trim()
    }
  }
  if (!data) return
  dispatchEvent(eventName, JSON.parse(data), handlers)
}

export async function streamChatReply(
  token: string,
  sessionId: string,
  message: string,
  handlers: StreamHandlers
) {
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ message })
  })

  if (!response.ok || !response.body) {
    throw new Error(await response.text())
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const chunk of chunks) {
      if (chunk.trim()) parseSseBlock(chunk, handlers)
    }
  }
  if (buffer.trim()) parseSseBlock(buffer, handlers)
}
