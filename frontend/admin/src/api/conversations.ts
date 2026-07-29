interface Conversation {
  id: string
  visitor_id: string
  visitor_external_userid: string
  status: string
  created_at: string
  updated_at: string
}

interface Message {
  id: string
  role: string
  content: string
  msg_type: string
  created_at: string
}

export async function getConversations(): Promise<Conversation[]> {
  const r = await fetch('/api/v1/conversations')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function getConversationMessages(conversationId: string): Promise<Message[]> {
  const r = await fetch(`/api/v1/conversations/${conversationId}/messages`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
