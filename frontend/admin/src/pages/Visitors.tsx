import { useEffect, useState } from 'react'
import { getVisitors, updateVisitor, type Visitor } from '../api/visitors'

interface EditState {
  id: string
  name: string
  notes: string
  tagInput: string
  tags: string[]
  ai_disabled: boolean
}

export default function Visitors() {
  const [visitors, setVisitors] = useState<Visitor[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [tagFilter, setTagFilter] = useState('')
  const [editing, setEditing] = useState<EditState | null>(null)
  const [saving, setSaving] = useState(false)

  const load = (s: string, t: string) => {
    setLoading(true)
    setError(null)
    getVisitors({ search: s || undefined, tag: t || undefined })
      .then(setVisitors)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load('', '')
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    load(search, tagFilter)
  }

  const openEdit = (v: Visitor) => {
    setEditing({
      id: v.id,
      name: v.name ?? '',
      notes: v.notes ?? '',
      tagInput: '',
      tags: [...v.tags],
      ai_disabled: v.ai_disabled,
    })
  }

  const addTag = () => {
    if (!editing) return
    const t = editing.tagInput.trim()
    if (t && !editing.tags.includes(t)) {
      setEditing({ ...editing, tags: [...editing.tags, t], tagInput: '' })
    } else {
      setEditing({ ...editing, tagInput: '' })
    }
  }

  const removeTag = (tag: string) => {
    if (!editing) return
    setEditing({ ...editing, tags: editing.tags.filter(t => t !== tag) })
  }

  const handleSave = async () => {
    if (!editing) return
    setSaving(true)
    try {
      const updated = await updateVisitor(editing.id, {
        name: editing.name.trim() || null,
        notes: editing.notes.trim() || null,
        tags: editing.tags,
        ai_disabled: editing.ai_disabled,
      })
      setVisitors(prev => prev.map(v => (v.id === updated.id ? updated : v)))
      setEditing(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const allTags = Array.from(new Set(visitors.flatMap(v => v.tags))).sort()

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">访客管理</h2>
          <p className="text-sm text-gray-500 mt-0.5">{visitors.length} 位访客</p>
        </div>
      </div>

      {/* Search & filter */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="搜索 ID 或姓名..."
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={tagFilter}
          onChange={e => setTagFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">全部标签</option>
          {allTags.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <button
          type="submit"
          className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors"
        >
          搜索
        </button>
      </form>

      {error && <p className="text-red-500 text-sm mb-3">错误：{error}</p>}

      {loading ? (
        <p className="text-gray-500 text-sm">加载中...</p>
      ) : visitors.length === 0 ? (
        <p className="text-gray-400 text-sm">暂无访客。</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['企业微信 ID', '姓名', '标签', '备注', 'AI 状态', '首次接触', '操作'].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {visitors.map(v => (
                <tr key={v.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-600 max-w-[140px] truncate">
                    {v.external_userid}
                  </td>
                  <td className="px-4 py-3 text-gray-900">
                    {v.name ?? <span className="text-gray-300">未填写</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {v.tags.length === 0
                        ? <span className="text-gray-300 text-xs">无</span>
                        : v.tags.map(t => (
                          <span key={t} className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                            {t}
                          </span>
                        ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-[160px] truncate">
                    {v.notes ?? <span className="text-gray-300">无</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      v.ai_disabled
                        ? 'bg-red-100 text-red-700'
                        : 'bg-green-100 text-green-700'
                    }`}>
                      {v.ai_disabled ? 'AI 停用' : 'AI 启用'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(v.created_at).toLocaleDateString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => openEdit(v)}
                      className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                    >
                      编辑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit modal */}
      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-96 p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">编辑访客信息</h3>

            <div>
              <label className="block text-xs text-gray-500 mb-1">姓名</label>
              <input
                value={editing.name}
                onChange={e => setEditing({ ...editing, name: e.target.value })}
                placeholder="未知访客"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">标签</label>
              <div className="flex flex-wrap gap-1 mb-1.5">
                {editing.tags.map(t => (
                  <span key={t} className="flex items-center gap-1 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                    {t}
                    <button onClick={() => removeTag(t)} className="hover:text-red-500 leading-none">×</button>
                  </span>
                ))}
              </div>
              <div className="flex gap-1">
                <input
                  value={editing.tagInput}
                  onChange={e => setEditing({ ...editing, tagInput: e.target.value })}
                  onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())}
                  placeholder="输入标签后按 Enter"
                  className="flex-1 border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <button
                  onClick={addTag}
                  className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50"
                >
                  添加
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">备注</label>
              <textarea
                value={editing.notes}
                onChange={e => setEditing({ ...editing, notes: e.target.value })}
                rows={3}
                placeholder="客服内部备注，访客不可见"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none"
              />
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={editing.ai_disabled}
                onChange={e => setEditing({ ...editing, ai_disabled: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm text-gray-700">停用 AI 自动回复（转为纯人工）</span>
            </label>

            <div className="flex gap-2 justify-end pt-1">
              <button
                onClick={() => setEditing(null)}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50 transition-colors"
              >
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
