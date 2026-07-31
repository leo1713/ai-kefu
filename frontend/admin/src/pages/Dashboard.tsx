import { useEffect, useState } from 'react'
import { getDailyStats, getOverview, type DailyStat, type OverviewStats } from '../api/stats'

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

function BarChart({ data, valueKey, label }: {
  data: DailyStat[]
  valueKey: 'conversations' | 'messages'
  label: string
}) {
  const max = Math.max(...data.map(d => d[valueKey]), 1)
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <p className="text-sm font-medium text-gray-700 mb-4">{label}（近7天）</p>
      <div className="flex items-end gap-1.5 h-32">
        {data.map(d => {
          const pct = Math.max((d[valueKey] / max) * 100, d[valueKey] > 0 ? 4 : 0)
          const dayLabel = d.date.slice(5)
          return (
            <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-xs text-gray-500">{d[valueKey]}</span>
              <div className="w-full flex items-end" style={{ height: '80px' }}>
                <div
                  className="w-full rounded-t bg-blue-400 transition-all"
                  style={{ height: `${pct}%` }}
                  title={`${d.date}: ${d[valueKey]}`}
                />
              </div>
              <span className="text-xs text-gray-400">{dayLabel}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [overview, setOverview] = useState<OverviewStats | null>(null)
  const [daily, setDaily] = useState<DailyStat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getOverview(), getDailyStats(7)])
      .then(([ov, d]) => { setOverview(ov); setDaily(d) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-gray-500 text-sm">加载中...</p>
  if (error) return <p className="text-red-500 text-sm">错误：{error}</p>
  if (!overview) return null

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">数据看板</h2>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="总对话数" value={overview.total_conversations} sub={`今日 ${overview.today_conversations} · 本周 ${overview.week_conversations}`} />
        <StatCard label="总消息数" value={overview.total_messages} />
        <StatCard label="访客数" value={overview.total_visitors} />
        <StatCard
          label="转人工率"
          value={`${overview.transfer_rate}%`}
          sub={`${overview.transferred_conversations} 次转人工`}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BarChart data={daily} valueKey="conversations" label="每日对话数" />
        <BarChart data={daily} valueKey="messages" label="每日消息数" />
      </div>
    </div>
  )
}
