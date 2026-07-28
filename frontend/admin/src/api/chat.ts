interface SSEEvent {
  event: string
  text?: string
  message_id?: string
  conversation_id?: string
  message?: string
}

export async function* streamChat(
  message: string,
  visitorId: string = 'web-test'
): AsyncGenerator<SSEEvent> {
  const response = await fetch('/api/v1/chat/completion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, visitor_id: visitorId }),
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}`)

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6)) as SSEEvent
        } catch {
          // skip malformed line
        }
      }
    }
  }
}
