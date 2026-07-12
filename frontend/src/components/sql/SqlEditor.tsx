import { useState } from 'react'
import { Play, Wand2, Copy, Check } from 'lucide-react'
import toast from 'react-hot-toast'

interface Props {
  sql: string
  onChange: (sql: string) => void
  onRun: (sql: string) => void
  loading?: boolean
}

export default function SqlEditor({ sql, onChange, onRun, loading }: Props) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-dark-surface border border-dark-border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-dark-border bg-dark-bg/50">
        <span className="text-xs font-mono text-dark-muted uppercase tracking-wider">SQL</span>
        <div className="flex items-center gap-2">
          <button onClick={copy}
            className="p-1.5 rounded text-dark-muted hover:text-white transition-all">
            {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button onClick={() => onRun(sql)} disabled={!sql || loading}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-brand-600 hover:bg-brand-700
              disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium transition-all">
            <Play className="w-3 h-3" fill="currentColor" />
            Run
          </button>
        </div>
      </div>
      <textarea
        value={sql}
        onChange={e => onChange(e.target.value)}
        spellCheck={false}
        className="w-full bg-transparent text-sm font-mono text-blue-300 p-4 resize-none outline-none
          min-h-[140px] scrollbar-thin placeholder-dark-muted/40"
        placeholder="SELECT * FROM your_table LIMIT 100"
        style={{ lineHeight: 1.6, tabSize: 2 }}
        onKeyDown={e => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault()
            onRun(sql)
          }
          if (e.key === 'Tab') {
            e.preventDefault()
            const start = e.currentTarget.selectionStart
            const end = e.currentTarget.selectionEnd
            const newVal = sql.substring(0, start) + '  ' + sql.substring(end)
            onChange(newVal)
          }
        }}
      />
      <div className="px-4 py-1.5 border-t border-dark-border bg-dark-bg/30">
        <p className="text-xs text-dark-muted">Ctrl+Enter to run · Only SELECT queries allowed</p>
      </div>
    </div>
  )
}
