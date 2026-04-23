import { create } from 'zustand'
import type { Incident, IncidentStatus } from '../api/client'

interface IncidentStore {
  incidents: Incident[]
  setIncidents: (incidents: Incident[]) => void
  addIncident: (incident: Incident) => void
  updateStatus: (id: string, status: string) => void
  highSeverityCount: number
}

export const useIncidentStore = create<IncidentStore>((set) => ({
  incidents: [],
  highSeverityCount: 0,
  setIncidents: (incidents) => {
    const highSeverityCount = incidents.filter(
      (inc) => inc.severity === 'HIGH' || inc.severity === 'CRITICAL'
    ).length
    set({ incidents, highSeverityCount })
  },
  addIncident: (incident) =>
    set((state) => ({
      incidents: [incident, ...state.incidents],
    })),
  updateStatus: (id, status) =>
    set((state) => ({
      incidents: state.incidents.map((inc) =>
        inc.id === id ? { ...inc, status: status as IncidentStatus } : inc
      ),
    })),
}))
