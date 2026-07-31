export interface OverviewStats {
  total_conversations: number
  today_conversations: number
  week_conversations: number
  transferred_conversations: number
  transfer_rate: number
  total_messages: number
  total_visitors: number
}

export interface DailyStat {
  date: string
  conversations: number
  messages: number
}

export async function getOverview(): Promise<OverviewStats> {
  const r = await fetch('/api/v1/stats/overview')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function getDailyStats(days = 7): Promise<DailyStat[]> {
  const r = await fetch(`/api/v1/stats/daily?days=${days}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
