import { useEffect, useState } from 'react'
import { listAgents, updateAgent } from '../api/agents'

interface Agent {
  id: string
  name: string
  system_prompt: string
  model: string
  temperature: number
  max_tokens: number
  is_default: boolean
}

interface EditState {
  name: string
  system_prompt: string
  model: string
  temperature: number
  max_tokens: number
}

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editState, setEditState] = useState<EditState | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const startEdit = (agent: Agent) => {
    setEditingId(agent.id)
    setEditState({
      name: agent.name,
      system_prompt: agent.system_prompt,
      model: agent.model,
      temperature: agent.temperature,
      max_tokens: agent.max_tokens,
    })
    setError(null)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditState(null)
  }

  const saveEdit = async (agentId: string) => {
    if (!editState) return
    setSaving(true)
    setError(null)
    try {
      const updated = await updateAgent(agentId, editState)
      setAgents(prev => prev.map(a => (a.id === agentId ? { ...a, ...updated } : a)))
      setEditingId(null)
      setEditState(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="text-gray-500 text-sm">加载中...</p>

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Agent 管理</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {agents.length === 0 && <p className="text-gray-400 text-sm">暂无 Agent。</p>}

      <div className="space-y-4">
        {agents.map(agent => {
          const isEditing = editingId === agent.id
          return (
            <div key={agent.id} className="bg-white border border-gray-200 rounded-lg p-5">
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <input
                      className="text-base font-semibold text-gray-900 border-b border-blue-400 outline-none"
                      value={editState!.name}
                      onChange={e => setEditState(s => s && { ...s, name: e.target.value })}
                    />
                  ) : (
                    <h3 className="text-base font-semibold text-gray-900">{agent.name}</h3>
                  )}
                  {agent.is_default && (
                    <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-600 rounded">
                      默认
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {isEditing ? (
                    <>
                      <button
                        onClick={() => saveEdit(agent.id)}
                        disabled={saving}
                        className="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 disabled:opacity-50"
                      >
                        {saving ? '保存中...' : '保存'}
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="px-3 py-1 bg-gray-100 text-gray-600 text-xs rounded hover:bg-gray-200"
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => startEdit(agent)}
                      className="px-3 py-1 bg-gray-100 text-gray-600 text-xs rounded hover:bg-gray-200"
                    >
                      编辑
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">系统提示词</label>
                  {isEditing ? (
                    <textarea
                      rows={6}
                      className="w-full text-sm border border-gray-300 rounded p-2 outline-none focus:border-blue-400 resize-y"
                      value={editState!.system_prompt}
                      onChange={e =>
                        setEditState(s => s && { ...s, system_prompt: e.target.value })
                      }
                    />
                  ) : (
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 rounded p-3 max-h-40 overflow-auto">
                      {agent.system_prompt || <span className="text-gray-400">（未设置）</span>}
                    </pre>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">模型</label>
                    {isEditing ? (
                      <input
                        className="w-full text-sm border border-gray-300 rounded p-1.5 outline-none focus:border-blue-400"
                        value={editState!.model}
                        onChange={e => setEditState(s => s && { ...s, model: e.target.value })}
                      />
                    ) : (
                      <p className="text-sm text-gray-700 font-mono">{agent.model}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Temperature</label>
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        className="w-full text-sm border border-gray-300 rounded p-1.5 outline-none focus:border-blue-400"
                        value={editState!.temperature}
                        onChange={e =>
                          setEditState(s => s && { ...s, temperature: parseFloat(e.target.value) })
                        }
                      />
                    ) : (
                      <p className="text-sm text-gray-700">{agent.temperature}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Max Tokens</label>
                    {isEditing ? (
                      <input
                        type="number"
                        min="1"
                        max="8096"
                        className="w-full text-sm border border-gray-300 rounded p-1.5 outline-none focus:border-blue-400"
                        value={editState!.max_tokens}
                        onChange={e =>
                          setEditState(s => s && { ...s, max_tokens: parseInt(e.target.value, 10) })
                        }
                      />
                    ) : (
                      <p className="text-sm text-gray-700">{agent.max_tokens}</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
