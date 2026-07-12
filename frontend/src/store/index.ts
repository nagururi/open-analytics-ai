import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, Dataset, QueryResult } from '../types'

interface AppState {
  user: User | null
  token: string | null
  theme: 'dark' | 'light'
  selectedDataset: Dataset | null
  availableModels: string[]
  selectedModel: string
  queryResults: QueryResult[]
  activeTab: string

  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setTheme: (theme: 'dark' | 'light') => void
  setSelectedDataset: (d: Dataset | null) => void
  setAvailableModels: (models: string[]) => void
  setSelectedModel: (m: string) => void
  addQueryResult: (r: QueryResult) => void
  setActiveTab: (t: string) => void
  logout: () => void
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      theme: 'dark',
      selectedDataset: null,
      availableModels: [],
      selectedModel: 'qwen2.5:1.5b',
      queryResults: [],
      activeTab: 'chat',

      setUser: (user) => set({ user }),
      setToken: (token) => {
        if (token) localStorage.setItem('token', token)
        else localStorage.removeItem('token')
        set({ token })
      },
      setTheme: (theme) => set({ theme }),
      setSelectedDataset: (d) => set({ selectedDataset: d }),
      setAvailableModels: (models) => set({ availableModels: models }),
      setSelectedModel: (m) => set({ selectedModel: m }),
      addQueryResult: (r) => set((s) => ({ queryResults: [r, ...s.queryResults.slice(0, 19)] })),
      setActiveTab: (t) => set({ activeTab: t }),
      logout: () => {
        localStorage.removeItem('token')
        set({ user: null, token: null, selectedDataset: null, queryResults: [] })
      },
    }),
    { name: 'analytics-store', partialize: (s) => ({ theme: s.theme, selectedModel: s.selectedModel }) }
  )
)
