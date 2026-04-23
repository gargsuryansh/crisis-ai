import React, { useMemo } from 'react'
import { useIncidents } from '../hooks/useIncidents'
import { HeroHighlight, Highlight } from '../components/HeroHighlight'
import { motion } from 'framer-motion'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line,
  ResponsiveContainer,
} from 'recharts'

const PIE_COLORS = ['#E74C3C', '#3498DB', '#F1C40F', '#2ECC71', '#9B59B6', '#E67E22']

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#C0392B',
  HIGH: '#E67E22',
  MEDIUM: '#F1C40F',
  LOW: '#27AE60',
}

export default function AnalyticsPage() {
  const { data, isLoading } = useIncidents()
  const incidents = data?.incidents || []

  const typeData = useMemo(
    () => {
      const counts: Record<string, number> = {}
      incidents.forEach((inc) => {
        counts[inc.type] = (counts[inc.type] || 0) + 1
      })
      return Object.entries(counts).map(([type, value]) => ({ type, value }))
    },
    [incidents],
  )

  const severityData = useMemo(
    () => {
      const order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const
      const counts: Record<string, number> = {}
      incidents.forEach((inc) => {
        counts[inc.severity] = (counts[inc.severity] || 0) + 1
      })
      return order.map((sev) => ({ severity: sev, value: counts[sev] || 0 }))
    },
    [incidents],
  )

  const hourlyData = useMemo(
    () => {
      const now = new Date()
      const buckets: Record<string, number> = {}
      incidents.forEach((inc) => {
        const d = new Date(inc.classified_at)
        const diffHours = (now.getTime() - d.getTime()) / (1000 * 60 * 60)
        if (diffHours <= 24 && diffHours >= 0) {
          const hourLabel = d.getHours().toString().padStart(2, '0') + ':00'
          buckets[hourLabel] = (buckets[hourLabel] || 0) + 1
        }
      })
      return Object.entries(buckets)
        .sort(([a], [b]) => (a < b ? -1 : 1))
        .map(([hour, value]) => ({ hour, value }))
    },
    [incidents],
  )

  const total = incidents.length
  const highSeverity = incidents.filter(
    (i) => i.severity === 'HIGH' || i.severity === 'CRITICAL',
  ).length
  const responded = incidents.filter(
    (i) => i.status === 'responded' || i.status === 'resolved',
  ).length
  const open = incidents.filter((i) => i.status === 'open').length

  return (
    <div className="p-6 space-y-6">
      <div className="rounded-2xl overflow-hidden mb-4 shadow-xl">
        <HeroHighlight containerClassName="h-60 bg-black">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: [20, -5, 0] }}
            transition={{ duration: 0.5, ease: [0.4, 0.0, 0.2, 1] }}
            className="text-2xl md:text-3xl lg:text-4xl font-bold text-white max-w-3xl leading-relaxed text-left px-8"
          >
            <Highlight className="text-white">
              CrisisAI Analytics
            </Highlight>{' '}
            helps authorities see{" "}
            <span className="text-indigo-400">where</span> and{" "}
            <span className="text-indigo-400">how severe</span> incidents are in real‑time.
          </motion.h1>
        </HeroHighlight>
      </div>

      <h2 className="text-xl font-semibold">Overview</h2>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-slate-500">Total Incidents</div>
          <div className="text-2xl font-bold">{total}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-slate-500">High Severity</div>
          <div className="text-2xl font-bold text-red-600">{highSeverity}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-slate-500">Responded</div>
          <div className="text-2xl font-bold text-emerald-600">{responded}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-slate-500">Open</div>
          <div className="text-2xl font-bold text-amber-600">{open}</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-sm font-semibold mb-2">Incident Types</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={typeData} dataKey="value" nameKey="type" outerRadius={80} label>
                {typeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-sm font-semibold mb-2">Severity Distribution</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={severityData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="severity" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value">
                {severityData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={SEVERITY_COLORS[entry.severity] || '#8884d8'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg shadow p-4 lg:col-span-2">
          <h2 className="text-sm font-semibold mb-2">Incidents in Last 24 Hours</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#3498DB" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {isLoading && <div className="text-xs text-slate-500">Loading analytics...</div>}
    </div>
  )
}