import { fetchWithAuth } from './client'

export interface WorkflowNode {
  id: string
  type: 'send_message' | 'condition' | 'tool_call' | 'end' | 'llm'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: Record<string, any>
  next?: string | null
  next_true?: string | null
  next_false?: string | null
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[]
  start: string
}

export interface Workflow {
  id: string
  name: string
  description: string | null
  trigger_keywords: string[]
  definition: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export async function listWorkflows(params?: {
  include_inactive?: boolean
}): Promise<Workflow[]> {
  const q = new URLSearchParams()
  if (params?.include_inactive) q.set('include_inactive', 'true')
  const r = await fetchWithAuth(`/api/v1/workflows${q.size ? `?${q}` : ''}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function createWorkflow(data: {
  name: string
  description?: string | null
  trigger_keywords: string[]
  definition: WorkflowDefinition
}): Promise<Workflow> {
  const r = await fetchWithAuth('/api/v1/workflows', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function getWorkflow(id: string): Promise<Workflow> {
  const r = await fetchWithAuth(`/api/v1/workflows/${id}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function updateWorkflow(
  id: string,
  data: {
    name?: string
    description?: string | null
    trigger_keywords?: string[]
    definition?: WorkflowDefinition
    is_active?: boolean
  }
): Promise<Workflow> {
  const r = await fetchWithAuth(`/api/v1/workflows/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function deleteWorkflow(id: string): Promise<void> {
  const r = await fetchWithAuth(`/api/v1/workflows/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}
