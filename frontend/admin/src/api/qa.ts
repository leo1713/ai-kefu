export interface QAPair {
  id: string
  question: string
  answer: string
  keywords: string[]
  category: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export async function listQA(params?: {
  search?: string
  category?: string
  include_inactive?: boolean
}): Promise<QAPair[]> {
  const q = new URLSearchParams()
  if (params?.search) q.set('search', params.search)
  if (params?.category) q.set('category', params.category)
  if (params?.include_inactive) q.set('include_inactive', 'true')
  const r = await fetch(`/api/v1/qa${q.size ? `?${q}` : ''}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function createQA(data: Omit<QAPair, 'id' | 'created_at' | 'updated_at'>): Promise<QAPair> {
  const r = await fetch('/api/v1/qa', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function updateQA(id: string, data: Partial<QAPair>): Promise<QAPair> {
  const r = await fetch(`/api/v1/qa/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function deleteQA(id: string): Promise<void> {
  const r = await fetch(`/api/v1/qa/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}

export async function batchImportQA(
  items: Array<{ question: string; answer: string; keywords?: string[]; category?: string }>
): Promise<{ imported: number }> {
  const r = await fetch('/api/v1/qa/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
