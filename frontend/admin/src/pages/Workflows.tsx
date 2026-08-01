import { useEffect, useState } from 'react'
import {
  createWorkflow,
  deleteWorkflow,
  listWorkflows,
  updateWorkflow,
  type Workflow,
  type WorkflowDefinition,
  type WorkflowNode,
} from '../api/workflows'

type NodeType = WorkflowNode['type']

const NODE_LABELS: Record<NodeType, string> = {
  send_message: '发消息',
  condition: '条件判断',
  tool_call: '调工具',
  llm: 'LLM 生成',
  end: '结束',
}

const TOOL_OPTIONS = ['query_order', 'query_payment', 'query_logistics', 'transfer_to_human']
const CONDITION_OPERATORS = ['contains', 'equals', 'starts_with']

function emptyNode(index: number): WorkflowNode {
  return { id: `n${index + 1}`, type: 'send_message', data: { text: '' }, next: null }
}

function parseDefinition(raw: string): WorkflowDefinition {
  try {
    return JSON.parse(raw) as WorkflowDefinition
  } catch {
    return { nodes: [], start: '' }
  }
}

interface NodeEditorProps {
  nodes: WorkflowNode[]
  onChange: (nodes: WorkflowNode[]) => void
}

function NodeEditor({ nodes, onChange }: NodeEditorProps) {
  const update = (i: number, patch: Partial<WorkflowNode>) => {
    const next = nodes.map((n, idx) => idx === i ? { ...n, ...patch } : n)
    onChange(next)
  }
  const updateData = (i: number, patch: Record<string, any>) => {
    update(i, { data: { ...nodes[i].data, ...patch } })
  }
  const remove = (i: number) => onChange(nodes.filter((_, idx) => idx !== i))
  const add = () => onChange([...nodes, emptyNode(nodes.length)])

  return (
    <div className="space-y-3">
      {nodes.map((node, i) => (
        <div key={node.id} className="border border-gray-200 rounded-lg p-3 bg-gray-50 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono bg-white border border-gray-300 px-1.5 py-0.5 rounded text-gray-500">{node.id}</span>
              <select
                value={node.type}
                onChange={e => update(i, { type: e.target.value as NodeType, data: {} })}
                className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
              >
                {(Object.keys(NODE_LABELS) as NodeType[]).map(t => (
                  <option key={t} value={t}>{NODE_LABELS[t]}</option>
                ))}
              </select>
            </div>
            <button onClick={() => remove(i)} className="text-xs text-red-400 hover:text-red-600 px-1">删除</button>
          </div>

          {node.type === 'send_message' && (
            <textarea
              value={node.data.text ?? ''}
              onChange={e => updateData(i, { text: e.target.value })}
              placeholder="发送给用户的消息内容"
              rows={2}
              className="w-full border border-gray-300 rounded px-2 py-1 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          )}

          {node.type === 'condition' && (
            <div className="grid grid-cols-3 gap-2">
              <input
                value={node.data.field ?? 'message'}
                onChange={e => updateData(i, { field: e.target.value })}
                placeholder="字段（如 message）"
                className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
              <select
                value={node.data.operator ?? 'contains'}
                onChange={e => updateData(i, { operator: e.target.value })}
                className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              >
                {CONDITION_OPERATORS.map(op => <option key={op} value={op}>{op}</option>)}
              </select>
              <input
                value={node.data.value ?? ''}
                onChange={e => updateData(i, { value: e.target.value })}
                placeholder="匹配值"
                className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
              <div className="col-span-3 grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-400 mb-0.5">满足 → 节点</label>
                  <input
                    value={node.next_true ?? ''}
                    onChange={e => update(i, { next_true: e.target.value || null })}
                    placeholder="如 n3"
                    className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-0.5">不满足 → 节点</label>
                  <input
                    value={node.next_false ?? ''}
                    onChange={e => update(i, { next_false: e.target.value || null })}
                    placeholder="如 n4"
                    className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                </div>
              </div>
            </div>
          )}

          {node.type === 'llm' && (
            <div className="space-y-1.5">
              <textarea
                value={node.data.prompt_template ?? ''}
                onChange={e => updateData(i, { prompt_template: e.target.value })}
                placeholder={`Prompt 模板，支持占位符：\n{{message}} — 用户消息\n{{tool_result_query_order}} — 工具结果`}
                rows={4}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-400 font-mono"
              />
              <p className="text-xs text-gray-400">占位符：<code>{'{{message}}'}</code>、<code>{'{{tool_result_工具名}}'}</code></p>
            </div>
          )}

          {node.type === 'tool_call' && (
            <div className="grid grid-cols-2 gap-2">
              <select
                value={node.data.tool ?? ''}
                onChange={e => updateData(i, { tool: e.target.value })}
                className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
              >
                <option value="">选择工具</option>
                {TOOL_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input
                value={node.data.params?.order_id ?? ''}
                onChange={e => updateData(i, { params: { order_id: e.target.value || undefined } })}
                placeholder="order_id（可用 {{message}}）"
                className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </div>
          )}

          {node.type !== 'condition' && node.type !== 'end' && (
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-400">下一节点：</span>
              <input
                value={node.next ?? ''}
                onChange={e => update(i, { next: e.target.value || null })}
                placeholder={`n${i + 2}`}
                className="w-20 border border-gray-300 rounded px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </div>
          )}
        </div>
      ))}
      <button
        onClick={add}
        className="w-full py-1.5 border border-dashed border-gray-300 text-sm text-gray-400 rounded hover:border-blue-400 hover:text-blue-500"
      >
        + 添加节点
      </button>
    </div>
  )
}

interface FormState {
  name: string
  description: string
  trigger_keywords: string
  nodes: WorkflowNode[]
}

const EMPTY_FORM: FormState = {
  name: '',
  description: '',
  trigger_keywords: '',
  nodes: [
    { id: 'n1', type: 'send_message', data: { text: '' }, next: 'n2' },
    { id: 'n2', type: 'end', data: {} },
  ],
}

export default function Workflows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [editing, setEditing] = useState<Workflow | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    setError(null)
    listWorkflows({ include_inactive: showInactive })
      .then(setWorkflows)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [showInactive])

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  const openEdit = (wf: Workflow) => {
    const def = parseDefinition(wf.definition)
    setEditing(wf)
    setForm({
      name: wf.name,
      description: wf.description ?? '',
      trigger_keywords: wf.trigger_keywords.join(', '),
      nodes: def.nodes.length ? def.nodes : EMPTY_FORM.nodes,
    })
    setShowForm(true)
  }

  const buildDefinition = (nodes: WorkflowNode[]): WorkflowDefinition => ({
    nodes,
    start: nodes[0]?.id ?? 'n1',
  })

  const handleSave = async () => {
    setSaving(true)
    try {
      const keywords = form.trigger_keywords.split(',').map(k => k.trim()).filter(Boolean)
      const definition = buildDefinition(form.nodes)
      if (editing) {
        const updated = await updateWorkflow(editing.id, {
          name: form.name.trim(),
          description: form.description.trim() || null,
          trigger_keywords: keywords,
          definition,
        })
        setWorkflows(prev => prev.map(wf => wf.id === updated.id ? updated : wf))
      } else {
        const created = await createWorkflow({
          name: form.name.trim(),
          description: form.description.trim() || null,
          trigger_keywords: keywords,
          definition,
        })
        setWorkflows(prev => [created, ...prev])
      }
      setShowForm(false)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除此工作流？')) return
    try {
      await deleteWorkflow(id)
      setWorkflows(prev => prev.filter(wf => wf.id !== id))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const handleToggle = async (wf: Workflow) => {
    try {
      const updated = await updateWorkflow(wf.id, { is_active: !wf.is_active })
      setWorkflows(prev => prev.map(w => w.id === updated.id ? updated : w))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">工作流</h2>
          <p className="text-sm text-gray-500 mt-0.5">{workflows.length} 个工作流</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)} className="rounded" />
            含停用
          </label>
          <button onClick={openCreate} className="px-3 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600">
            + 新建工作流
          </button>
        </div>
      </div>

      {error && <p className="text-red-500 text-sm mb-3">错误：{error}</p>}

      {loading ? (
        <p className="text-gray-500 text-sm">加载中...</p>
      ) : workflows.length === 0 ? (
        <p className="text-gray-400 text-sm">暂无工作流。点击"新建工作流"创建第一个。</p>
      ) : (
        <div className="space-y-2">
          {workflows.map(wf => {
            const def = parseDefinition(wf.definition)
            return (
              <div key={wf.id} className={`bg-white border rounded-lg p-4 ${!wf.is_active ? 'opacity-50' : ''}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{wf.name}</p>
                    {wf.description && <p className="text-xs text-gray-500 mt-0.5">{wf.description}</p>}
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      {wf.trigger_keywords.map(kw => (
                        <span key={kw} className="text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 px-1.5 py-0.5 rounded">
                          触发：{kw}
                        </span>
                      ))}
                      <span className="text-xs text-gray-400">{def.nodes.length} 个节点</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <button
                      onClick={() => handleToggle(wf)}
                      className={`text-xs px-2 py-1 rounded border transition-colors ${
                        wf.is_active
                          ? 'border-gray-200 text-gray-500 hover:bg-gray-50'
                          : 'border-green-200 text-green-600 hover:bg-green-50'
                      }`}
                    >
                      {wf.is_active ? '停用' : '启用'}
                    </button>
                    <button
                      onClick={() => openEdit(wf)}
                      className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(wf.id)}
                      className="text-xs px-2 py-1 rounded border border-red-200 text-red-500 hover:bg-red-50"
                    >
                      删除
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl space-y-4 p-6 my-8">
            <h3 className="text-base font-semibold text-gray-900">
              {editing ? '编辑工作流' : '新建工作流'}
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">名称 *</label>
                <input
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="工作流名称"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">描述</label>
                <input
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="可选描述"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">触发关键词（逗号分隔）</label>
                <input
                  value={form.trigger_keywords}
                  onChange={e => setForm(f => ({ ...f, trigger_keywords: e.target.value }))}
                  placeholder="如：查订单,订单状态,我的快递"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <p className="text-xs text-gray-400 mt-0.5">用户消息包含任意一个关键词时触发此工作流</p>
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-2">节点列表（按顺序执行）</label>
              <NodeEditor
                nodes={form.nodes}
                onChange={nodes => setForm(f => ({ ...f, nodes }))}
              />
            </div>

            <div className="flex gap-2 justify-end pt-1 border-t border-gray-100">
              <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900">
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.name.trim()}
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
