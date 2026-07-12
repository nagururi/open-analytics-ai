import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import api from '../utils/api'
import toast from 'react-hot-toast'
import { BarChart3, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { setUser, setToken } = useStore()
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register'
      const payload = mode === 'login'
        ? { username: form.username, password: form.password }
        : form
      const r = await api.post(endpoint, payload)
      setToken(r.data.access_token)
      setUser(r.data.user)
      navigate('/')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-800 mb-4">
            <BarChart3 className="w-8 h-8 text-blue-400" />
          </div>
          <h1 className="text-3xl font-bold text-white">Open Analytics AI</h1>
          <p className="text-dark-muted mt-1">Natural Language to SQL Platform</p>
        </div>

        {/* Card */}
        <div className="bg-dark-surface border border-dark-border rounded-2xl p-8">
          {/* Tabs */}
          <div className="flex gap-1 mb-6 bg-dark-bg rounded-lg p-1">
            {(['login', 'register'] as const).map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`flex-1 py-2 rounded-md text-sm font-medium transition-all capitalize
                  ${mode === m ? 'bg-brand-700 text-white' : 'text-dark-muted hover:text-white'}`}>
                {m}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-muted mb-1">Username</label>
              <input value={form.username} onChange={e => setForm({...form, username: e.target.value})}
                required placeholder="admin"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2.5 text-white
                  placeholder-dark-muted focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500" />
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-dark-muted mb-1">Email</label>
                <input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})}
                  required placeholder="you@company.com"
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2.5 text-white
                    placeholder-dark-muted focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500" />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-dark-muted mb-1">Password</label>
              <input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})}
                required placeholder="••••••••"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2.5 text-white
                  placeholder-dark-muted focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500" />
            </div>

            <button type="submit" disabled={loading}
              className="w-full py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed
                text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <p className="mt-4 text-center text-xs text-dark-muted">
            Default: <span className="font-mono text-blue-400">admin / admin123</span>
          </p>
        </div>

        <p className="text-center text-xs text-dark-muted mt-6">
          100% Open Source · Self-Hosted · Runs Offline
        </p>
      </div>
    </div>
  )
}
