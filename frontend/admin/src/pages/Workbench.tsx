import { useEffect, useRef, useState } from 'react'
import { getToken, login } from '../api/auth'
import {
  getConversationMessages,
  getConversations,
  replyMessage,
  type Conversation,
  type Message,
} from '../api/conversations'

export default function Workbench() {
  const [token, setToken] = useState<string | null>(getToken())
  if (!token) return <LoginPanel onLogin={() => setToken(getToken())} />
  return <WorkbenchPanel token={token} />
}

function LoginPanel({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(username, password)
      onLogin()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center h-full">
      <form
        onSubmit={handleSubmit}
        className="bg-white p-8 rounded-lg border border-gray-200 w-80 space-y-4"
      >
        <h2 className="text-lg font-semibold text-gray-900">客服工作台</h2>
        <div>
          <label className="block text-xs text-gray-500 mb-1">用户名</label>
          <input
            required
            value={username}
            onChange={e => setUsername(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">密码</label>
          <input
            required
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        {error && <p className="text-xs text-red-500">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-blue-500 text-white rounded text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors"
        >
          {loading ? '登录中...' : '登录'}
        </button>
      </form>
    </div>
  )
}

function WorkbenchPanel({ token }: { token: string }) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'open' | 'closed'>('connecting')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getConversations('transferred').then(setConversations).catch(console.error)
  }, [])

  useEffect(() => {
    if (!selectedId) return
    setMessages([])
    getConversationMessages(selectedId).then(setMessages).catch(console.error)
  }, [selectedId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/staff?token=${token}`)
    setWsStatus('connecting')

    ws.onopen = () => setWsStatus('open')
    ws.onclose = () => setWsStatus('closed')

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data as string)
        if (data.event === 'new_message') {
          setSelectedId(prev => {
            if (prev === data.conversation_id) {
              setMessages(msgs => [...msgs, data.message as Message])
            }
            return prev
          })
          setConversations(prev => {
            const idx = prev.findIndex(c => c.id === data.conversation_id)
            if (idx === -1) return prev
            const updated = [...prev]
            updated[idx] = { ...updated[idx], updated_at: new Date().toISOString() }
            return [updated[idx], ...updated.filter((_, i) => i !== idx)]
          })
        } else if (data.event === 'conversation_transferred') {
          const conv = data.conversation as Conversation
          setConversations(prev =>
            prev.some(c => c.id === conv.id) ? prev : [conv, ...prev]
          )
        }
      } catch {
        // ignore malformed frames
      }
    }

    const hb = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, 25000)

    return () => {
      clearInterval(hb)
      ws.close()
    }
  }, [token])

  const handleSend = async () => {
    if (!selectedId || !input.trim() || sending) return
    const content = input.trim()
    setInput('')
    setSending(true)
    try {
      const msg = await replyMessage(selectedId, content)
      setMessages(prev => [...prev, msg])
    } catch (err) {
      console.error('Reply failed:', err)
    } finally {
      setSending(false)
    }
  }

  const selectedConv = conversations.find(c => c.id === selectedId)

  return (
    <div className="flex h-full -m-6 overflow-hidden">
      {/* Left: conversation list */}
      <div className="w-72 border-r border-gray-200 bg-white flex flex-col flex-shrink-0">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">待接会话</h2>
            <p className="text-xs text-gray-400 mt-0.5">{conversations.length} 个转人工</p>
          </div>
          <span
            className={`w-2 h-2 rounded-full ${
              wsStatus === 'open' ? 'bg-green-400' : wsStatus === 'connecting' ? 'bg-yellow-400' : 'bg-red-400'
            }`}
            title={wsStatus}
          />
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <p className="text-center text-gray-400 text-xs mt-10">暂无待接会话</p>
          ) : (
            conversations.map(c => (
              <button
                key={c.id}
                onClick={() => setSelectedId(c.id)}
                className={`w-full text-left px-4 py-3 border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                  selectedId === c.id ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''
                }`}
              >
                <div className="text-sm font-medium text-gray-900 truncate">
                  {c.visitor_external_userid}
                </div>
                <div className="text-xs text-gray-400 mt-0.5 truncate">
                  {c.transfer_reason ?? '转人工'}
                </div>
                <div className="text-xs text-gray-300 mt-0.5">
                  {new Date(c.updated_at).toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Right: message area */}
      <div className="flex-1 flex flex-col bg-gray-50 min-w-0">
        {!selectedConv ? (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            选择左侧会话开始接待
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="px-5 py-3 bg-white border-b border-gray-200 flex items-center gap-3">
              <span className="text-sm font-medium text-gray-900">
                {selectedConv.visitor_external_userid}
              </span>
              <span className="text-xs text-gray-400 truncate max-w-xs">
                {selectedConv.transfer_reason}
              </span>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              {messages.map(msg => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'staff' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className="max-w-sm">
                    <div
                      className={`px-3 py-2 rounded-2xl text-sm whitespace-pre-wrap break-words ${
                        msg.role === 'staff'
                          ? 'bg-blue-500 text-white'
                          : 'bg-white text-gray-900 border border-gray-200'
                      }`}
                    >
                      {msg.content}
                    </div>
                    <div
                      className={`text-xs text-gray-400 mt-0.5 ${
                        msg.role === 'staff' ? 'text-right' : 'text-left'
                      }`}
                    >
                      {msg.role === 'staff' ? '我' : msg.role === 'assistant' ? 'AI' : '访客'}
                      {' · '}
                      {new Date(msg.created_at).toLocaleTimeString('zh-CN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-5 py-3 bg-white border-t border-gray-200 flex gap-2">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                placeholder="输入回复，Enter 发送"
                disabled={sending}
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={sending || !input.trim()}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors"
              >
                {sending ? '发送中' : '发送'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
