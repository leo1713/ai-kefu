import { fetchWithAuth } from './client'

interface Agent {
  id: string
  name: string
  system_prompt: string
  model: string
  temperature: number
  max_tokens: number
  is_default: boolean
  slug: string | null
  created_at: string
  updated_at: string
}

interface AgentUpdate {
  name?: string
  system_prompt?: string
  model?: string
  temperature?: number
  max_tokens?: number
  slug?: string | null
}

export async function listAgents(): Promise<Agent[]> {
  const r = await fetchWithAuth('/api/v1/agents')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function updateAgent(agentId: string, data: AgentUpdate): Promise<Agent> {
  const r = await fetchWithAuth(`/api/v1/agents/${agentId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${r.status}`)
  }
  return r.json()
}
