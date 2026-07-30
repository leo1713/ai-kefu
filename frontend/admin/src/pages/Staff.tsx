import { useEffect, useState } from 'react'
import { createStaff, getStaffList, updateStaffStatus, type Staff } from '../api/conversations'

interface FormData {
  username: string
  display_name: string
  password: string
  wecom_userid: string
}

const EMPTY_FORM: FormData = { username: '', display_name: '', password: '', wecom_userid: '' }

export default function StaffPage() {
  const [staffList, setStaffList] = useState<Staff[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<FormData>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [togglingId, setTogglingId] = useState<string | null>(null)

  const load = (includeInactive: boolean) => {
    setLoading(true)
    setError(null)
    getStaffList(includeInactive)
      .then(setStaffList)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(showInactive)
  }, [showInactive])

  const handleToggleActive = async (staff: Staff) => {
    setTogglingId(staff.id)
    try {
      const updated = await updateStaffStatus(staff.id, !staff.is_active)
      setStaffList(prev => prev.map(s => (s.id === updated.id ? updated : s)))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setTogglingId(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    setSubmitting(true)
    try {
      const payload = {
        username: form.username.trim(),
        display_name: form.display_name.trim(),
        password: form.password,
        wecom_userid: form.wecom_userid.trim() || undefined,
      }
      const created = await createStaff(payload)
      setStaffList(prev => [created, ...prev])
      setForm(EMPTY_FORM)
      setShowForm(false)
    } catch (e) {
      setFormError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const activeCount = staffList.filter(s => s.is_active).length

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">客服管理</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {activeCount} 位在线客服 · 共 {staffList.length} 人
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={e => setShowInactive(e.target.checked)}
              className="rounded"
            />
            显示停用账号
          </label>
          <button
            onClick={() => {
              setShowForm(v => !v)
              setFormError(null)
              setForm(EMPTY_FORM)
            }}
            className="px-3 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 transition-colors"
          >
            + 添加客服
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-white border border-gray-200 rounded-lg p-4 mb-4 grid grid-cols-2 gap-3"
        >
          <h3 className="col-span-2 text-sm font-medium text-gray-700 mb-1">新建客服账号</h3>
          <div>
            <label className="block text-xs text-gray-500 mb-1">用户名 *</label>
            <input
              required
              value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              placeholder="登录用，英文数字"
              className="w-full border border-gray-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">显示名称 *</label>
            <input
              required
              value={form.display_name}
              onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))}
              placeholder="例：张小丽"
              className="w-full border border-gray-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">密码 *</label>
            <input
              required
              type="password"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              placeholder="至少 6 位"
              className="w-full border border-gray-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">企业微信 UserID</label>
            <input
              value={form.wecom_userid}
              onChange={e => setForm(f => ({ ...f, wecom_userid: e.target.value }))}
              placeholder="可选，用于通知转接"
              className="w-full border border-gray-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>
          {formError && (
            <p className="col-span-2 text-xs text-red-500">错误：{formError}</p>
          )}
          <div className="col-span-2 flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50 transition-colors"
            >
              {submitting ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      )}

      {/* Error */}
      {error && <p className="text-red-500 text-sm mb-3">错误：{error}</p>}

      {/* Table */}
      {loading ? (
        <p className="text-gray-500 text-sm">加载中...</p>
      ) : staffList.length === 0 ? (
        <p className="text-gray-400 text-sm">暂无客服账号。</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['显示名称', '用户名', '企业微信 ID', '状态', '创建时间', '操作'].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {staffList.map(s => (
                <tr key={s.id} className={`hover:bg-gray-50 ${!s.is_active ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3 font-medium text-gray-900">{s.display_name}</td>
                  <td className="px-4 py-3 font-mono text-gray-600 text-xs">{s.username}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {s.wecom_userid ?? <span className="text-gray-300">未配置</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {s.is_active ? '在线' : '停用'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(s.created_at).toLocaleDateString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggleActive(s)}
                      disabled={togglingId === s.id}
                      className={`text-xs px-2 py-1 rounded border transition-colors disabled:opacity-50 ${
                        s.is_active
                          ? 'border-red-200 text-red-600 hover:bg-red-50'
                          : 'border-green-200 text-green-600 hover:bg-green-50'
                      }`}
                    >
                      {togglingId === s.id ? '处理中...' : s.is_active ? '停用' : '启用'}
                    </button>
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
