import { useEffect, useState } from 'react'
import { LayoutDashboard, Plus, Loader2, Trash2 } from 'lucide-react'
import api from '../../utils/api'
import { Dashboard } from '../../types'
import toast from 'react-hot-toast'
import { useStore } from '../../store'

export default function DashboardPanel() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [loading, setLoading] = useState(true)
  const { selectedDataset } = useStore()

  useEffect(() => {
    api.get('/dashboard').then(r => setDashboards(r.data)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const deleteDashboard = async (id: string) => {
    if (!confirm('Delete this dashboard?')) return
    try {
      await api.delete(`/dashboard/${id}`)
      setDashboards(d => d.filter(x => x.id !== id))
      toast.success('Dashboard deleted')
    } catch { toast.error('Delete failed') }
  }

  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Dashboards</h2>
          <p className="text-dark-muted text-sm">Saved analytics dashboards</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
        </div>
      ) : dashboards.length === 0 ? (
        <div className="text-center py-16 text-dark-muted">
          <LayoutDashboard className="w-14 h-14 mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium text-white/70 mb-2">No dashboards yet</p>
          <p className="text-sm">Ask questions in the chat to generate charts,<br/>then dashboards will appear here automatically.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {dashboards.map(d => (
            <div key={d.id} className="bg-dark-surface border border-dark-border rounded-xl p-5 hover:border-blue-400/30 transition-all group">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2 min-w-0">
                  <LayoutDashboard className="w-5 h-5 text-blue-400 shrink-0" />
                  <span className="text-white font-medium truncate">{d.name}</span>
                </div>
                <button onClick={() => deleteDashboard(d.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded text-dark-muted hover:text-red-400 transition-all">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              {d.description && <p className="text-dark-muted text-sm mb-3">{d.description}</p>}
              <div className="text-xs text-dark-muted space-y-1">
                <p>By {d.created_by} · {d.is_public ? 'Public' : 'Private'}</p>
                <p>{new Date(d.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
