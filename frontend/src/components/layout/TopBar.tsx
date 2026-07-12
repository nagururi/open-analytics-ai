import { Sun, Moon, Wifi, WifiOff, ChevronDown } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useStore } from '../../store'
import api from '../../utils/api'

export default function TopBar() {
  const { theme, setTheme, selectedDataset, availableModels, selectedModel, setSelectedModel } = useStore()
  const [ollamaOk, setOllamaOk] = useState(false)

  useEffect(() => {
    api.get('/health/ollama').then(r => setOllamaOk(r.data.status === 'ok')).catch(() => setOllamaOk(false))
  }, [])

  return (
    <div className="h-12 bg-dark-surface border-b border-dark-border flex items-center px-4 gap-3 shrink-0">
      {/* Dataset badge */}
      <div className="flex-1 text-sm">
        {selectedDataset ? (
          <span className="text-white font-medium">
            📊 <span className="text-blue-400">{selectedDataset.name}</span>
            <span className="text-dark-muted ml-2">{selectedDataset.row_count?.toLocaleString()} rows</span>
          </span>
        ) : (
          <span className="text-dark-muted">No dataset selected — upload data to get started</span>
        )}
      </div>

      {/* Model selector */}
      {availableModels.length > 0 && (
        <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
          className="text-xs bg-dark-bg border border-dark-border rounded-lg px-2 py-1.5 text-dark-muted
            focus:outline-none focus:border-brand-500 cursor-pointer">
          {availableModels.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      )}

      {/* Ollama status */}
      <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full
        ${ollamaOk ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
        {ollamaOk ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
        <span className="hidden md:block">{ollamaOk ? 'Ollama' : 'Offline'}</span>
      </div>

      {/* Theme toggle */}
      <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        className="p-1.5 rounded-lg text-dark-muted hover:text-white hover:bg-dark-bg transition-all">
        {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>
    </div>
  )
}
