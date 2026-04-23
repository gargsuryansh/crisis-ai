import { Navigate, Route, Routes, NavLink } from 'react-router-dom'
import MapPage from './pages/MapPage'
import IncidentsPage from './pages/IncidentsPage'
import ChatbotPage from './pages/ChatbotPage'
import AnalyticsPage from './pages/AnalyticsPage'
import { useIncidentStore } from './store/incidentStore'
import { HeroHighlight } from './components/HeroHighlight'

function Sidebar() {
  const highSeverityCount = useIncidentStore((s) => s.highSeverityCount)

  const linkBase =
    'flex items-center px-4 py-3 mb-2 rounded-lg text-sm font-medium transition-all duration-200'
  const inactive = 'text-slate-400 hover:bg-slate-800 hover:text-white'
  const active = 'bg-blue-600 text-white shadow-md'

  return (
    <div className="w-64 bg-slate-900 text-white flex flex-col min-h-screen shadow-2xl z-10">
      <div className="px-6 py-6 border-b border-slate-800">
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <span className="text-red-500">⚠</span> CrisisAI
        </h1>
        <div className="text-xs text-slate-400 mt-1 tracking-wider uppercase font-semibold">
          Authority Dashboard
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 overflow-y-auto">
        <NavLink
          to="/map"
          className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}
        >
          🌍 Live Map
        </NavLink>

        <NavLink
          to="/incidents"
          className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}
        >
          📋 Incidents Table
          {highSeverityCount > 0 && (
            <span className="ml-auto inline-flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 animate-pulse">
              {highSeverityCount}
            </span>
          )}
        </NavLink>

        <NavLink
          to="/chatbot"
          className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}
        >
          🤖 AI Chatbot
        </NavLink>

        <NavLink
          to="/analytics"
          className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}
        >
          📊 Analytics
        </NavLink>
      </nav>

      <div className="px-6 py-4 text-xs text-slate-500 border-t border-slate-800 bg-slate-950">
        Google Solution Challenge 2026
      </div>
    </div>
  )
}

export default function App() {
  return (
    <div className="flex min-h-screen bg-white font-sans text-slate-900 overflow-hidden">
      <Sidebar />
      <HeroHighlight 
        containerClassName="flex-1 h-screen overflow-y-auto !justify-start !items-start" 
        className="w-full h-full"
      >
        <main className="w-full h-full">
          <Routes>
            <Route path="/" element={<Navigate to="/map" replace />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/incidents" element={<IncidentsPage />} />
            <Route path="/chatbot" element={<ChatbotPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
          </Routes>
        </main>
      </HeroHighlight>
    </div>
  )
}