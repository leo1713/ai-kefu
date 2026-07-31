import { useEffect, useState } from 'react'
import {
  batchImportQA,
  createQA,
  deleteQA,
  listQA,
  updateQA,
  type QAPair,
} from '../api/qa'

interface FormState {
  question: string
  answer: string
  keywords: string
  category: string
  is_active: boolean
}

const EMPTY_FORM: FormState = {
  question: '',
  answer: '',
  keywords: '',
  category: '',
  is_active: true,
}

export default function QAPage() {
  const [pairs, setPairs] = useState<QAPair[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [editing, setEditing] = useState<QAPair | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showBatch, setShowBatch] = useState(false)
  const [batchJson, setBatchJson] = useState('')
  const [batchMsg, setBatchMsg] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    listQA({ search: search || undefined, include_inactive: showInactive })
      .then(setPairs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [showInactive])

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  const openEdit = (p: QAPair) => {
    setEditing(p)
    setForm({
      question: p.question,
      answer: p.answer,
      keywords: p.keywords.join(', '),
      category: p.category ?? '',
      is_active: p.is_active,
    })
    setShowForm(true)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const data = {
        question: form.question.trim(),
        answer: form.answer.trim(),
        keywords: form.keywords.split(',').map(k => k.trim()).filter(Boolean),
        category: form.category.trim() || null,
        is_active: form.is_active,
      }
      if (editing) {
        const updated = await updateQA(editing.id, data)
        setPairs(prev => prev.map(p => p.id === updated.id ? updated : p))
      } else {
        const created = await createQA(data)
        setPairs(prev => [created, ...prev])
      }
      setShowForm(false)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除此 QA 条目？')) return
    try {
      await deleteQA(id)
      setPairs(prev => prev.filter(p => p.id !== id))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const handleToggle = async (p: QAPair) => {
    try {
      const updated = await updateQA(p.id, { is_active: !p.is_active })
      setPairs(prev => prev.map(x => x.id === updated.id ? updated : x))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const handleBatchImport = async () => {
    setBatchMsg(null)
    try {
      const items = JSON.parse(batchJson)
      if (!Array.isArray(items)) throw new Error('JSON 必须是数组')
      const result = await batchImportQA(items)
      setBatchMsg(`成功导入 ${result.imported} 条`)
      setBatchJson('')
      load()
    } catch (e) {
      setBatchMsg(`错误：${(e as Error).message}`)
    }
  }

  const filtered = pairs.filter(p =>
    !search ||
    p.question.toLowerCase().includes(search.toLowerCase()) ||
    p.answer.toLowerCase().includes(search.toLowerCase())
  )

  const categories = Array.from(new Set(pairs.map(p => p.category).filter(Boolean))).sort()

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">QA 知识库</h2>
          <p className="text-sm text-gray-500 mt-0.5">{filtered.length} 条 QA</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)} className="rounded" />
            含停用
          </label>
          <button onClick={() => setShowBatch(v => !v)} className="px-3 py-1.5 border border-gray-300 text-sm rounded hover:bg-gray-50">
            批量导入
          </button>
          <button onClick={openCreate} className="px-3 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600">
            + 新增
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-4">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="搜索问题或答案..."
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Batch import panel */}
      {showBatch && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4 space-y-3">
          <p className="text-sm font-medium text-gray-700">批量导入 JSON</p>
          <p className="text-xs text-gray-500">格式：<code>[{'{'}{"question":"...","answer":"...","category":"...","keywords":["kw1"]}{'}'}]</code></p>
          <textarea
            value={batchJson}
            onChange={e => setBatchJson(e.target.value)}
            rows={6}
            placeholder='[{"question": "退款流程是什么？", "answer": "申请退款请..."}]'
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none"
          />
          {batchMsg && (
            <p className={`text-xs ${batchMsg.startsWith('错误') ? 'text-red-500' : 'text-green-600'}`}>
              {batchMsg}
            </p>
          )}
          <button
            onClick={handleBatchImport}
            disabled={!batchJson.trim()}
            className="px-4 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50"
          >
            导入
          </button>
        </div>
      )}

      {error && <p className="text-red-500 text-sm mb-3">错误：{error}</p>}

      {loading ? (
        <p className="text-gray-500 text-sm">加载中...</p>
      ) : filtered.length === 0 ? (
        <p className="text-gray-400 text-sm">暂无 QA 条目。</p>
      ) : (
        <div className="space-y-2">
          {filtered.map(p => (
            <div
              key={p.id}
              className={`bg-white border rounded-lg p-4 ${!p.is_active ? 'opacity-50' : ''}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">Q</span>
                    <p className="text-sm font-medium text-gray-900">{p.question}</p>
                  </div>
                  <div className="flex items-start gap-2 mb-2">
                    <span className="text-xs font-medium text-green-600 bg-green-50 px-1.5 py-0.5 rounded mt-0.5 flex-shrink-0">A</span>
                    <p className="text-sm text-gray-600 whitespace-pre-wrap">{p.answer}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {p.category && (
                      <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                        {p.category}
                      </span>
                    )}
                    {p.keywords.map(kw => (
                      <span key={kw} className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">
                        #{kw}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <button
                    onClick={() => handleToggle(p)}
                    className={`text-xs px-2 py-1 rounded border transition-colors ${
                      p.is_active
                        ? 'border-gray-200 text-gray-500 hover:bg-gray-50'
                        : 'border-green-200 text-green-600 hover:bg-green-50'
                    }`}
                  >
                    {p.is_active ? '停用' : '启用'}
                  </button>
                  <button
                    onClick={() => openEdit(p)}
                    className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="text-xs px-2 py-1 rounded border border-red-200 text-red-500 hover:bg-red-50"
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg space-y-4 p-6">
            <h3 className="text-base font-semibold text-gray-900">
              {editing ? '编辑 QA' : '新增 QA'}
            </h3>

            <div>
              <label className="block text-xs text-gray-500 mb-1">问题 *</label>
              <input
                value={form.question}
                onChange={e => setForm(f => ({ ...f, question: e.target.value }))}
                placeholder="用户可能提出的问题"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1">标准答案 *</label>
              <textarea
                value={form.answer}
                onChange={e => setForm(f => ({ ...f, answer: e.target.value }))}
                rows={5}
                placeholder="标准答案（Claude 会在此基础上调整语气）"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">分类</label>
                <input
                  value={form.category}
                  onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                  placeholder="如：退款、物流"
                  list="qa-categories"
                  className="w-full border border-gray-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <datalist id="qa-categories">
                  {categories.map(c => <option key={c} value={c!} />)}
                </datalist>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">关键词（逗号分隔）</label>
                <input
                  value={form.keywords}
                  onChange={e => setForm(f => ({ ...f, keywords: e.target.value }))}
                  placeholder="退款,退货"
                  className="w-full border border-gray-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
              </div>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                className="rounded"
              />
              <span className="text-sm text-gray-700">启用（AI 回复时参考此 QA）</span>
            </label>

            <div className="flex gap-2 justify-end pt-1">
              <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900">
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.question.trim() || !form.answer.trim()}
                className="px-4 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50"
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
