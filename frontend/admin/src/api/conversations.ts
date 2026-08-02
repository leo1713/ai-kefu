import { fetchWithAuth } from './client'

export interface Conversation {
  id: string
  visitor_id: string
  visitor_external_userid: string
  status: string
  assigned_staff_id: string | null
  transfer_reason: string | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  role: string
  content: string
  msg_type: string
  created_at: string
}

export interface Staff {
  id: string
  username: string
  display_name: string
  wecom_userid: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export async function getConversations(status?: string): Promise<Conversation[]> {
  const url = status ? `/api/v1/conversations?status=${status}` : '/api/v1/conversations'
  const r = await fetchWithAuth(url)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function getConversationMessages(conversationId: string): Promise<Message[]> {
  const r = await fetchWithAuth(`/api/v1/conversations/${conversationId}/messages`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function transferConversation(conversationId: string, reason: string): Promise<Conversation> {
  const r = await fetchWithAuth(`/api/v1/conversations/${conversationId}/transfer`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function assignStaff(conversationId: string, staffId: string): Promise<Conversation> {
  const r = await fetchWithAuth(`/api/v1/conversations/${conversationId}/assign`, {
    method: 'POST',
    body: JSON.stringify({ staff_id: staffId }),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function getStaffList(includeInactive = false): Promise<Staff[]> {
  const r = await fetchWithAuth(`/api/v1/staff?include_inactive=${includeInactive}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function createStaff(data: {
  username: string
  display_name: string
  password: string
  wecom_userid?: string
}): Promise<Staff> {
  const r = await fetchWithAuth('/api/v1/staff', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${r.status}`)
  }
  return r.json()
}

export async function closeConversation(conversationId: string): Promise<Conversation> {
  const r = await fetchWithAuth(`/api/v1/conversations/${conversationId}/close`, {
    method: 'PATCH',
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function updateStaffStatus(staffId: string, isActive: boolean): Promise<Staff> {
  const r = await fetchWithAuth(`/api/v1/staff/${staffId}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function replyMessage(conversationId: string, content: string): Promise<Message> {
  const r = await fetchWithAuth(`/api/v1/conversations/${conversationId}/reply`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
