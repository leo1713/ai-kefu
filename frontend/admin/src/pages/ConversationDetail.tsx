import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getConversationMessages } from '../api/conversations'

interface Message {
  id: string
  role: string
  content: string
  msg_type: string
  created_at: string
}

export default function ConversationDetail() {
  const { id } = useParams<{ id: string }>()
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!id) return
    getConversationMessages(id)
      .then(msgs => {
        const sorted = [...msgs].sort(
          (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        )
        setMessages(sorted)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 mb-4">
        <Link to="/conversations" className="text-blue-500 hover:underline text-sm">
          ← 返回对话列表
        </Link>
        <span className="text-gray-400 text-sm">|</span>
        <span className="text-sm text-gray-500 font-mono truncate">{id}</span>
      </div>

      {loading && <p className="text-gray-500 text-sm">加载中...</p>}
      {error && <p className="text-red-500 text-sm">错误：{error}</p>}

      {!loading && !error && messages.length === 0 && (
        <p className="text-gray-400 text-sm">暂无消息记录。</p>
      )}

      {!loading && !error && messages.length > 0 && (
        <div className="flex-1 overflow-auto space-y-3 pb-4">
          {messages.map(msg => {
            const isUser = msg.role === 'user'
            return (
              <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                  <span className="text-xs text-gray-400 px-1">
                    {isUser ? '访客' : 'AI'}
                    {' · '}
                    {new Date(msg.created_at).toLocaleString('zh-CN')}
                  </span>
                  <div
                    className={`rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap break-words ${
                      isUser
                        ? 'bg-blue-500 text-white rounded-tr-sm'
                        : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              </div>
            )
          })}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
