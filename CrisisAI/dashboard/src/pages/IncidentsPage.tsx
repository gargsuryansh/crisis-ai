import React, { useState, useEffect } from 'react'
import { useIncidents } from '../hooks/useIncidents'
import { useIncidentStore } from '../store/incidentStore'
import { markResponded } from '../api/client'
import { HeroHighlight, Highlight } from '../components/HeroHighlight'
import { motion } from 'framer-motion'

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-500',
  HIGH: 'bg-orange-500',
  MEDIUM: 'bg-yellow-500',
  LOW: 'bg-green-500',
}

export default function IncidentsPage() {
  const [severity, setSeverity] = useState<string>('')
  const [type, setType] = useState<string>('')
  const [area, setArea] = useState<string>('')

  const { data, isLoading, refetch } = useIncidents({
    severity: severity || undefined,
    type: type || undefined,
    area: area || undefined,
  })

  const { setIncidents } = useIncidentStore()

  useEffect(() => {
    if (data?.incidents) {
      setIncidents(data.incidents)
    }
  }, [data, setIncidents])

  const handleMarkResponded = async (id: string) => {
    if (!confirm('Mark this incident as responded?')) return
    try {
      await markResponded(id, 'Responded via dashboard')
      refetch()
    } catch (err) {
      console.error('Failed to update status:', err)
      alert('Failed to update status')
    }
  }

  return (
    <div className="p-6">
      <div className="rounded-2xl overflow-hidden mb-6 shadow-xl">
        <HeroHighlight containerClassName="h-60 bg-black">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: [20, -5, 0] }}
            transition={{ duration: 0.5, ease: [0.4, 0.0, 0.2, 1] }}
            className="text-2xl md:text-3xl lg:text-4xl font-bold text-white max-w-3xl leading-relaxed text-left px-8"
          >
            <Highlight className="text-white">
              Incident Management
            </Highlight>{' '}
            Explore and respond to <span className="text-indigo-400">active reports</span> across the region.
          </motion.h1>
        </HeroHighlight>
      </div>

      <h2 className="text-xl font-semibold mb-4">Active Incidents</h2>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-lg shadow mb-6 flex gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Severity</label>
          <select value={severity} onChange={(e) => setSeverity(e.target.value)}
            className="border border-slate-300 rounded px-3 py-2 w-40">
            <option value="">All</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Type</label>
          <select value={type} onChange={(e) => setType(e.target.value)}
            className="border border-slate-300 rounded px-3 py-2 w-40">
            <option value="">All Types</option>
            <option value="fire">Fire</option>
            <option value="flood">Flood</option>
            <option value="medical">Medical</option>
            <option value="accident">Accident</option>
            <option value="chemical">Chemical</option>
            <option value="violence">Violence</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Area</label>
          <input
            type="text"
            value={area}
            onChange={(e) => setArea(e.target.value)}
            placeholder="e.g. Mumbai"
            className="border border-slate-300 rounded px-3 py-2 w-40"
          />
        </div>

        <button
          onClick={() => refetch()}
          className="bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700"
        >
          Apply Filters
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Severity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Area</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Source</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Time</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="text-center py-8">Loading incidents...</td></tr>
            ) : data?.incidents?.map((inc) => (
              <tr key={inc.id} className="border-b hover:bg-slate-50">
                <td className="px-6 py-4 text-sm font-mono text-slate-500">{inc.id.slice(0,8)}...</td>
                <td className="px-6 py-4 font-medium capitalize">{inc.type}</td>
                <td className="px-6 py-4">
                  <span className={`px-3 py-1 text-xs font-semibold text-white rounded-full ${SEVERITY_COLORS[inc.severity]}`}>
                    {inc.severity}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm">{inc.location.area_name}</td>
                <td className="px-6 py-4 text-sm text-slate-500">{inc.source_platform}</td>
                <td className="px-6 py-4 text-sm text-slate-500">{new Date(inc.classified_at).toLocaleString()}</td>
                <td className="px-6 py-4">
                  <span className={`px-3 py-1 text-xs rounded-full ${inc.status === 'resolved' ? 'bg-green-100 text-green-700' : inc.status === 'responded' ? 'bg-blue-100 text-blue-700' : 'bg-yellow-100 text-yellow-700'}`}>
                    {inc.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  {inc.status === 'open' && (
                    <button
                      onClick={() => handleMarkResponded(inc.id)}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm px-4 py-1.5 rounded"
                    >
                      Mark Responded
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
