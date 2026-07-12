import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useStore } from './store'
import LoginPage from './pages/LoginPage'
import MainPage from './pages/MainPage'
import api from './utils/api'

function App() {
  const { theme, user, setUser, setAvailableModels } = useStore()

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    if (!user) {
      api.get('/auth/me').then(r => setUser(r.data)).catch(() => {})
    }
    api.get('/llm/models').then(r => setAvailableModels(r.data.models)).catch(() => {})
  }, [])

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage />} />
      <Route path="/*" element={user ? <MainPage /> : <Navigate to="/login" />} />
    </Routes>
  )
}

export default App
