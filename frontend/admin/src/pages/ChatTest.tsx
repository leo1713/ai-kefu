import { useRef, useState } from 'react'
import { streamChat } from '../api/chat'

interface Message {
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
}

export default function ChatTest() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const visitorId = useRef(`web-${Math.random().toString(36).slice(2, 8)}`)

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setLoading(true)

    setMessages(prev => [...prev, { role: 'user', text }])
    setMessages(prev => [...prev, { role: 'assistant', text: '', streaming: true }])

    try {
      for await (const event of streamChat(text, visitorId.current)) {
        if (event.event === 'chat.content_chunk' && event.text) {
          setMessages(prev => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last?.role === 'assistant') {
              next[next.length - 1] = { ...last, text: last.text + event.text }
            }
            return next
          })
        }
        if (event.event === 'chat.completed') {
          setMessages(prev => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last?.role === 'assistant') {
              next[next.length - 1] = { ...last, streaming: false }
            }
            return next
          })
        }
        if (event.event === 'chat.error') {
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = {
              role: 'assistant',
              text: `错误：${event.message ?? '未知错误'}`,
              streaming: false,
            }
            return next
          })
        }
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">SSE 流式聊天测试</h2>

      <div className="flex-1 overflow-y-auto space-y-3 mb-4 p-4 bg-gray-50 rounded-lg min-h-64">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm text-center mt-8">发送消息开始测试</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-xs px-4 py-2 rounded-2xl text-sm whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white text-gray-900 border border-gray-200'
              }`}
            >
              {msg.text}
              {msg.streaming && (
                <span className="inline-block w-1 h-4 ml-0.5 bg-gray-400 animate-pulse align-text-bottom" />
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="输入消息，按 Enter 发送"
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-blue-600 transition-colors"
        >
          发送
        </button>
      </div>
    </div>
  )
}
