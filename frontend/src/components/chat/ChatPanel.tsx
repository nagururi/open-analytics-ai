import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Sparkles, Database, ChevronDown, ChevronUp, Code2, Lightbulb } from 'lucide-react'
import { useStore } from '../../store'
import api from '../../utils/api'
import { QueryResult } from '../../types'
import ResultTable from '../table/ResultTable'
import ChartGrid from '../charts/ChartGrid'
import SqlEditor from '../sql/SqlEditor'
import toast from 'react-hot-toast'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  result?: QueryResult
  sql?: string
  explanation?: string
  loading?: boolean
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showSQL, setShowSQL] = useState<Record<string, boolean>>({})
  const [editingSQL, setEditingSQL] = useState<Record<string, string>>({})
  const { selectedDataset, selectedModel, addQueryResult } = useStore()
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (selectedDataset) {
      loadSuggestions()
    }
  }, [selectedDataset?.id])

  const loadSuggestions = async () => {
    if (!selectedDataset) return
    try {
      const r = await api.get(`/query/suggestions/${selectedDataset.id}`)
      setSuggestions(r.data.suggestions)
    } catch {}
  }

  const sendMessage = async (question: string) => {
    if (!question.trim()) return
    if (!selectedDataset) {
      toast.error('Please select a dataset first')
      return
    }

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: question }
    const loadingMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: '', loading: true }

    setMessages(m => [...m, userMsg, loadingMsg])
    setInput('')
    setLoading(true)

    // Build conversation history
    const history = messages.slice(-6).map(m => ({
      role: m.role,
      content: m.content || ''
    }))

    try {
      const r = await api.post('/query/nl', {
        question,
        dataset_id: selectedDataset.id,
        model: selectedModel,
        conversation_history: history,
      })

      const result: QueryResult = r.data
      addQueryResult(result)

      setMessages(m => m.map(msg =>
        msg.id === loadingMsg.id
          ? {
              ...msg,
              loading: false,
              content: result.explanation || (result.success ? 'Here are the results:' : 'Query failed.'),
              result,
              sql: result.generated_sql,
              explanation: result.explanation,
            }
          : msg
      ))
    } catch (err: any) {
      setMessages(m => m.map(msg =>
        msg.id === loadingMsg.id
          ? { ...msg, loading: false, content: `Error: ${err.response?.data?.detail || 'Request failed'}` }
          : msg
      ))
    } finally {
      setLoading(false)
    }
  }

  const runSQL = async (msgId: string, sql: string) => {
    if (!selectedDataset) return
    try {
      const r = await api.post('/query/execute', { sql, dataset_id: selectedDataset.id })
      setMessages(m => m.map(msg =>
        msg.id === msgId ? { ...msg, result: r.data } : msg
      ))
      toast.success('Query executed')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Execution failed')
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4">
        {messages.length === 0 && (
          <WelcomeScreen
            dataset={selectedDataset?.name}
            suggestions={suggestions}
            onSuggest={sendMessage}
          />
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="bg-brand-700 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[70%] text-sm">
                {msg.content}
              </div>
            ) : (
              <div className="flex-1 max-w-[98%] space-y-3">
                {msg.loading ? (
                  <div className="bg-dark-surface border border-dark-border rounded-2xl rounded-tl-sm p-4 flex items-center gap-3">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                    <span className="text-dark-muted text-sm">Generating SQL with {selectedModel}...</span>
                  </div>
                ) : (
                  <>
                    {/* Explanation */}
                    {msg.content && (
                      <div className="bg-dark-surface border border-dark-border rounded-2xl rounded-tl-sm px-4 py-2.5 text-dark-text text-sm">
                        {msg.content}
                      </div>
                    )}

                    {/* SQL block */}
                    {msg.sql && (
                      <div className="bg-dark-bg border border-dark-border rounded-xl overflow-hidden">
                        <button
                          onClick={() => setShowSQL(s => ({ ...s, [msg.id]: !s[msg.id] }))}
                          className="w-full flex items-center justify-between px-4 py-2 text-xs text-dark-muted hover:text-white transition-colors">
                          <span className="flex items-center gap-2">
                            <Code2 className="w-3.5 h-3.5 text-blue-400" />
                            View SQL
                          </span>
                          {showSQL[msg.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>
                        {showSQL[msg.id] && (
                          <div className="px-4 pb-3">
                            <SqlEditor
                              sql={editingSQL[msg.id] ?? msg.sql}
                              onChange={sql => setEditingSQL(s => ({ ...s, [msg.id]: sql }))}
                              onRun={sql => runSQL(msg.id, sql)}
                            />
                          </div>
                        )}
                      </div>
                    )}

                    {/* Charts */}
                    {msg.result?.charts && msg.result.charts.length > 0 && (
                      <ChartGrid charts={msg.result.charts} />
                    )}

                    {/* Table */}
                    {msg.result && (
                      <ResultTable result={msg.result} />
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-dark-border bg-dark-surface p-4">
        {!selectedDataset && (
          <div className="mb-3 text-center text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg py-2">
            ⚠️ No dataset selected — go to Upload to add data
          </div>
        )}
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder={selectedDataset ? `Ask about ${selectedDataset.name}...` : 'Upload data first...'}
              disabled={!selectedDataset || loading}
              rows={1}
              className="w-full bg-dark-bg border border-dark-border rounded-xl px-4 py-3 pr-12 text-white
                placeholder-dark-muted resize-none focus:outline-none focus:border-brand-500 focus:ring-1
                focus:ring-brand-500 disabled:opacity-50 text-sm scrollbar-thin"
              style={{ maxHeight: 120, lineHeight: 1.5 }}
              onInput={e => {
                const t = e.currentTarget
                t.style.height = 'auto'
                t.style.height = Math.min(t.scrollHeight, 120) + 'px'
              }}
            />
          </div>
          <button onClick={() => sendMessage(input)} disabled={!input.trim() || loading || !selectedDataset}
            className="p-3 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed
              text-white transition-all shrink-0">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
        </div>
        <p className="text-xs text-dark-muted mt-2 text-center">Enter to send · Shift+Enter for new line · Powered by Ollama</p>
      </div>
    </div>
  )
}

function WelcomeScreen({ dataset, suggestions, onSuggest }: {
  dataset?: string; suggestions: string[]; onSuggest: (q: string) => void
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 space-y-8">
      <div>
        <div className="w-16 h-16 rounded-2xl bg-brand-800 flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-8 h-8 text-blue-400" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">
          {dataset ? `Analyzing: ${dataset}` : 'Ask Anything About Your Data'}
        </h2>
        <p className="text-dark-muted max-w-md">
          {dataset
            ? 'Ask questions in plain English — AI generates SQL, executes it, and creates charts automatically'
            : 'Upload an Excel or CSV file, then start asking questions in natural language'}
        </p>
      </div>

      {suggestions.length > 0 && (
        <div className="w-full max-w-2xl">
          <div className="flex items-center gap-2 mb-3 justify-center">
            <Lightbulb className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-dark-muted">Suggested Questions</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {suggestions.slice(0, 6).map((s, i) => (
              <button key={i} onClick={() => onSuggest(s)}
                className="text-left text-sm px-4 py-3 bg-dark-surface border border-dark-border rounded-xl
                  text-dark-muted hover:text-white hover:border-blue-400/50 transition-all">
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {!dataset && (
        <div className="grid grid-cols-3 gap-4 text-xs text-dark-muted max-w-lg w-full">
          {['Upload Excel/CSV', 'AI Generates SQL', 'Charts Auto-Created'].map((step, i) => (
            <div key={i} className="bg-dark-surface border border-dark-border rounded-xl p-3">
              <div className="w-6 h-6 rounded-full bg-brand-800 text-blue-400 flex items-center justify-center font-bold text-xs mx-auto mb-2">
                {i + 1}
              </div>
              {step}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
