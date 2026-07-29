interface KnowledgeDocument {
  id: string
  collection_id: string
  filename: string
  file_type: string
  created_at: string
}

export async function listDocuments(): Promise<KnowledgeDocument[]> {
  const r = await fetch('/api/v1/knowledge/documents')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function uploadDocument(file: File): Promise<KnowledgeDocument> {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch('/api/v1/knowledge/upload', { method: 'POST', body: form })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${r.status}`)
  }
  return r.json()
}

export async function deleteDocument(documentId: string): Promise<void> {
  const r = await fetch(`/api/v1/knowledge/documents/${documentId}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}
