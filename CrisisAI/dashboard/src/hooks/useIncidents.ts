import { useQuery } from '@tanstack/react-query'
import { fetchIncidents, type IncidentListResponse } from '../api/client'

export interface IncidentFilters {
  severity?: string
  type?: string
  area?: string
  limit?: number
  offset?: number
}

export function useIncidents(filters?: IncidentFilters) {
  return useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => fetchIncidents(filters).then((r) => r.data as IncidentListResponse),
    refetchInterval: 3000,
    staleTime: 2000,
  })
}
