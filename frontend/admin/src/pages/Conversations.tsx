import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Conversation, closeConversation, getConversations } from '../api/conversations'

const STATUS_LABEL: Record<string, string> = {
  active: '进行中',
  closed: '已关闭',
  transferred: '已转人工',
}

const STATUS_STYLE: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  transferred: 'bg-yellow-100 text-yellow-700',
  closed: 'bg-gray-100 text-gray-500',
}

type FilterStatus = 'all' | 'active' | 'transferred' | 'closed'

const FILTERS: { key: FilterStatus; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'active', label: '进行中' },
  { key: 'transferred', label: '已转人工' },
  { key: 'closed', label: '已关闭' },
]

export default function Conversations() {
  const [convs, setConvs] = useState<Conversation[]>([])
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [closingId, setClosingId] = useState<string | null>(null)

  const load = (status: FilterStatus) => {
    setLoading(true)
    setError(null)
    getConversations(status === 'all' ? undefined : status)
      .then(setConvs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(filter)
  }, [filter])

  const handleClose = async (id: string) => {
    if (!confirm('确认关闭此会话？')) return
    setClosingId(id)
    try {
      await closeConversation(id)
      load(filter)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setClosingId(null)
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-gray-900">对话记录</h2>
        <span className="text-sm text-gray-500">{convs.length} 条会话</span>
      </div>

      <div className="flex gap-2 mb-4">
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
              filter === f.key
                ? 'bg-blue-500 text-white border-blue-500'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && <p className="text-gray-500 text-sm">加载中...</p>}

      {!loading && convs.length === 0 && (
        <p className="text-gray-400 text-sm">暂无对话记录。</p>
      )}

      {!loading && convs.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['访客 ID', '状态', '转人工原因', '最后更新', '操作'].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {convs.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-gray-700 truncate max-w-[160px]">
                    {c.visitor_external_userid}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        STATUS_STYLE[c.status] ?? 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {STATUS_LABEL[c.status] ?? c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-[200px] truncate">
                    {c.transfer_reason ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(c.updated_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Link
                        to={`/conversations/${c.id}`}
                        className="text-blue-500 hover:underline text-xs"
                      >
                        详情
                      </Link>
                      {c.status !== 'closed' && (
                        <button
                          onClick={() => handleClose(c.id)}
                          disabled={closingId === c.id}
                          className="text-gray-400 hover:text-red-500 text-xs disabled:opacity-40"
                        >
                          关闭
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
