import { useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import ChatPanel from '../components/chat/ChatPanel'
import UploadPanel from '../components/upload/UploadPanel'
import SchemaPanel from '../components/dashboard/SchemaPanel'
import HistoryPanel from '../components/dashboard/HistoryPanel'
import DashboardPanel from '../components/dashboard/DashboardPanel'
import { useStore } from '../store'

export default function MainPage() {
  const { activeTab } = useStore()

  const panels: Record<string, React.ReactNode> = {
    chat: <ChatPanel />,
    upload: <UploadPanel />,
    schema: <SchemaPanel />,
    history: <HistoryPanel />,
    dashboards: <DashboardPanel />,
  }

  return (
    <div className="flex h-screen bg-dark-bg overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-hidden">
          {panels[activeTab] || <ChatPanel />}
        </main>
      </div>
    </div>
  )
}
