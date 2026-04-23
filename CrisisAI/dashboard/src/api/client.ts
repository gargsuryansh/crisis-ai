import axios from 'axios'

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type IncidentStatus = 'open' | 'responded' | 'resolved'

export interface IncidentLocation {
  lat: number
  lng: number
  area_name: string
}

export interface Incident {
  id: string
  type: string
  severity: Severity
  location: IncidentLocation
  source_text: string
  source_platform: string
  classified_at: string
  status: IncidentStatus
  confidence: number
}

export interface IncidentListResponse {
  incidents: Incident[]
  total: number
  high_severity_count: number
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

export const fetchIncidents = (params?: {
  severity?: string
  type?: string
  area?: string
  limit?: number
  offset?: number
}) => apiClient.get<IncidentListResponse>('/incidents', { params })

export const markResponded = (id: string, note: string) =>
  apiClient.patch(`/incidents/${id}`, {
    status: 'responded',
    authority_note: note,
  })

export const queryBot = (
  question: string,
  filters?: { area?: string; type?: string; severity?: string | null },
  use_grounding?: boolean,
) =>
  apiClient.post('/query', {
    question,
    filters: filters || {},
    use_grounding: use_grounding ?? false,
    stream: false,
  })

export default apiClient
