import { MessageSquare, Upload, Database, History, LayoutDashboard, LogOut, BarChart3, Settings } from 'lucide-react'
import { useStore } from '../../store'

const items = [
  { id: 'chat', icon: MessageSquare, label: 'Ask AI' },
  { id: 'upload', icon: Upload, label: 'Upload' },
  { id: 'schema', icon: Database, label: 'Schema' },
  { id: 'history', icon: History, label: 'History' },
  { id: 'dashboards', icon: LayoutDashboard, label: 'Dashboards' },
]

export default function Sidebar() {
  const { activeTab, setActiveTab, logout, user } = useStore()

  return (
    <div className="w-16 md:w-56 bg-dark-surface border-r border-dark-border flex flex-col shrink-0 transition-all">
      {/* Logo */}
      <div className="p-4 border-b border-dark-border flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-brand-700 flex items-center justify-center shrink-0">
          <BarChart3 className="w-5 h-5 text-blue-400" />
        </div>
        <span className="hidden md:block font-bold text-white text-sm truncate">Open Analytics AI</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-2 space-y-1">
        {items.map(({ id, icon: Icon, label }) => (
          <button key={id} onClick={() => setActiveTab(id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-medium
              ${activeTab === id
                ? 'bg-brand-700/30 text-blue-400 border border-brand-700/50'
                : 'text-dark-muted hover:text-white hover:bg-dark-bg'}`}>
            <Icon className="w-5 h-5 shrink-0" />
            <span className="hidden md:block">{label}</span>
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-2 border-t border-dark-border space-y-1">
        <div className="hidden md:flex items-center gap-2 px-3 py-2">
          <div className="w-7 h-7 rounded-full bg-brand-800 flex items-center justify-center text-xs font-bold text-blue-400">
            {user?.username?.[0]?.toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white text-xs font-medium truncate">{user?.username}</p>
            <p className="text-dark-muted text-xs capitalize">{user?.role}</p>
          </div>
        </div>
        <button onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-dark-muted hover:text-red-400 hover:bg-red-500/10 transition-all text-sm">
          <LogOut className="w-5 h-5 shrink-0" />
          <span className="hidden md:block">Sign Out</span>
        </button>
      </div>
    </div>
  )
}
