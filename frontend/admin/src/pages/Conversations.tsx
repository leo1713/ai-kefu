import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getConversations } from '../api/conversations'

interface Conversation {
  id: string
  visitor_external_userid: string
  status: string
  updated_at: string
}

const STATUS_LABEL: Record<string, string> = {
  active: '进行中',
  closed: '已关闭',
  transferred: '已转人工',
}

export default function Conversations() {
  const [convs, setConvs] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getConversations()
      .then(setConvs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-gray-500 text-sm">加载中...</p>
  if (error) return <p className="text-red-500 text-sm">错误：{error}</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-gray-900">对话记录</h2>
        <span className="text-sm text-gray-500">{convs.length} 条会话</span>
      </div>

      {convs.length === 0 ? (
        <p className="text-gray-400 text-sm">暂无对话记录。</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['访客 ID', '状态', '最后更新', '操作'].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {convs.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-gray-700 truncate max-w-xs">
                    {c.visitor_external_userid}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        c.status === 'active'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {STATUS_LABEL[c.status] ?? c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(c.updated_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/conversations/${c.id}`}
                      className="text-blue-500 hover:underline text-xs"
                    >
                      查看详情
                    </Link>
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
