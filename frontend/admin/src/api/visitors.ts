import { fetchWithAuth } from './client'

export interface Visitor {
  id: string
  external_userid: string
  name: string | null
  avatar: string | null
  ai_disabled: boolean
  tags: string[]
  notes: string | null
  created_at: string
  updated_at: string
}

export async function getVisitors(params?: {
  search?: string
  tag?: string
  limit?: number
}): Promise<Visitor[]> {
  const q = new URLSearchParams()
  if (params?.search) q.set('search', params.search)
  if (params?.tag) q.set('tag', params.tag)
  if (params?.limit) q.set('limit', String(params.limit))
  const r = await fetchWithAuth(`/api/v1/visitors${q.size ? `?${q}` : ''}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function updateVisitor(
  id: string,
  data: Partial<Pick<Visitor, 'name' | 'tags' | 'notes' | 'ai_disabled'>>
): Promise<Visitor> {
  const r = await fetchWithAuth(`/api/v1/visitors/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
