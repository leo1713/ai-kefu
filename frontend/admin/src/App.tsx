import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Agents from './pages/Agents'
import ChatTest from './pages/ChatTest'
import ConversationDetail from './pages/ConversationDetail'
import Conversations from './pages/Conversations'
import Dashboard from './pages/Dashboard'
import Knowledge from './pages/Knowledge'
import Staff from './pages/Staff'
import Visitors from './pages/Visitors'
import Workflows from './pages/Workflows'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50">
        <nav className="w-56 bg-white border-r border-gray-200 p-4">
          <h1 className="text-lg font-bold text-gray-900 mb-6">AI 客服</h1>
          <ul className="space-y-1">
            {[
              { to: '/', label: '概览' },
              { to: '/conversations', label: '对话记录' },
              { to: '/agents', label: 'Agent 管理' },
              { to: '/knowledge', label: '知识库' },
              { to: '/visitors', label: '访客管理' },
              { to: '/staff', label: '客服管理' },
              { to: '/workflows', label: '工作流' },
              { to: '/chat-test', label: '聊天测试' },
            ].map(({ to, label }) => (
              <li key={to}>
                <Link
                  to={to}
                  className="block px-3 py-2 rounded text-sm text-gray-700 hover:bg-gray-100"
                >
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/conversations" element={<Conversations />} />
            <Route path="/conversations/:id" element={<ConversationDetail />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/knowledge" element={<Knowledge />} />
            <Route path="/visitors" element={<Visitors />} />
            <Route path="/staff" element={<Staff />} />
            <Route path="/workflows" element={<Workflows />} />
            <Route path="/chat-test" element={<ChatTest />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

