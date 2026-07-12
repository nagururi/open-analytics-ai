import { useEffect, useState } from 'react'
import { Clock, Star, CheckCircle, XCircle, Play, Loader2 } from 'lucide-react'
import api from '../../utils/api'
import { QueryHistoryItem } from '../../types'
import { formatMs } from '../../utils/api'
import { useStore } from '../../store'
import toast from 'react-hot-toast'

export default function HistoryPanel() {
  const [history, setHistory] = useState<QueryHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'favorites'>('all')

  useEffect(() => {
    api.get('/query/history')
      .then(r => setHistory(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const toggleFav = async (id: string) => {
    try {
      const r = await api.post(`/query/history/${id}/favorite`)
      setHistory(h => h.map(item => item.id === id ? { ...item, is_favorite: r.data.is_favorite ? 1 : 0 } : item))
    } catch { toast.error('Failed to update favorite') }
  }

  const filtered = filter === 'favorites' ? history.filter(h => h.is_favorite) : history

  return (
    <div className="h-full overflow-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Query History</h2>
          <p className="text-dark-muted text-sm">{history.length} queries</p>
        </div>
        <div className="flex gap-1 bg-dark-bg rounded-lg p-1">
          {(['all', 'favorites'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded text-sm capitalize transition-all
                ${filter === f ? 'bg-dark-surface text-white' : 'text-dark-muted hover:text-white'}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-dark-muted">
          <Clock className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p>{filter === 'favorites' ? 'No favorites yet' : 'No queries yet'}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(item => (
            <div key={item.id} className="bg-dark-surface border border-dark-border rounded-xl p-4 hover:border-blue-400/30 transition-all">
              <div className="flex items-start justify-between gap-3 mb-2">
                <p className="text-white text-sm font-medium">{item.natural_language}</p>
                <div className="flex items-center gap-2 shrink-0">
                  {item.is_valid ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-400" />
                  )}
                  <button onClick={() => toggleFav(item.id)}
                    className={`transition-colors ${item.is_favorite ? 'text-yellow-400' : 'text-dark-muted hover:text-yellow-400'}`}>
                    <Star className="w-4 h-4" fill={item.is_favorite ? 'currentColor' : 'none'} />
                  </button>
                </div>
              </div>
              <div className="bg-dark-bg rounded-lg p-3 mb-2">
                <code className="text-blue-300 text-xs font-mono line-clamp-2">{item.generated_sql}</code>
              </div>
              <div className="flex items-center gap-4 text-xs text-dark-muted">
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{formatMs(item.execution_time_ms)}</span>
                <span>{item.row_count?.toLocaleString()} rows</span>
                <span className="ml-auto">{new Date(item.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
