import React, { useEffect, useState } from 'react'
import { GoogleMap, LoadScript, Marker, InfoWindow } from '@react-google-maps/api'
import { useIncidents } from '../hooks/useIncidents'
import { useWebSocket } from '../hooks/useWebSocket'
import { useIncidentStore } from '../store/incidentStore'
import type { Incident } from '../api/client'
import { HeroHighlight, Highlight } from '../components/HeroHighlight'
import { motion } from 'framer-motion'

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#C0392B',
  HIGH: '#E67E22',
  MEDIUM: '#F1C40F',
  LOW: '#27AE60',
}

const markerIcon: google.maps.Symbol = {
  path: 0, // Equals google.maps.SymbolPath.CIRCLE
  scale: 8,
  fillOpacity: 1,
  strokeWeight: 1,
  strokeColor: '#ffffff',
}

export default function MapPage() {
  useWebSocket()
  const { data } = useIncidents()
  const { setIncidents } = useIncidentStore()
  const incidents = useIncidentStore((s) => s.incidents)
  const [selected, setSelected] = useState<Incident | null>(null)

  useEffect(() => {
    if (data?.incidents) {
      setIncidents(data.incidents)
    }
  }, [data, setIncidents])

    return (
    <div className="p-6 h-screen box-border flex flex-col">
      <div className="rounded-2xl overflow-hidden mb-4 shrink-0 shadow-xl">
        <HeroHighlight containerClassName="h-60 bg-black">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: [20, -5, 0] }}
            transition={{ duration: 0.5, ease: [0.4, 0.0, 0.2, 1] }}
            className="text-2xl md:text-3xl lg:text-4xl font-bold text-white max-w-3xl leading-relaxed text-left px-8"
          >
            <Highlight className="text-white">
              Live Incident Map
            </Highlight>{' '}
            Monitor <span className="text-indigo-400">real-time locations</span> and severity of crisis events.
          </motion.h1>
        </HeroHighlight>
      </div>

      <div className="flex-1 bg-white rounded-lg shadow overflow-hidden relative min-h-[400px]">
        <LoadScript googleMapsApiKey={import.meta.env.VITE_GOOGLE_MAPS_API_KEY}>
          <GoogleMap
            mapContainerStyle={{ width: '100%', height: '100%' }}
            center={{ lat: 20.5937, lng: 78.9629 }}
            zoom={5}
          >
            {incidents.map((inc) => (
              <Marker
                key={inc.id}
                position={{ lat: inc.location.lat, lng: inc.location.lng }}
                icon={{
                  ...markerIcon,
                  fillColor: SEVERITY_COLORS[inc.severity] || '#3498DB',
                }}
                onClick={() => setSelected(inc)}
              />
            ))}

            {selected && (
              <InfoWindow
                position={{
                  lat: selected.location.lat,
                  lng: selected.location.lng,
                }}
                onCloseClick={() => setSelected(null)}
              >
                <div className="text-sm p-1">
                  <div className="font-semibold text-slate-900">
                    {selected.type.toUpperCase()}
                  </div>
                  <div className="text-xs text-slate-600">
                    {selected.location.area_name} • {selected.severity}
                  </div>
                  <div className="mt-1 text-xs text-slate-700">
                    {selected.source_text}
                  </div>
                </div>
              </InfoWindow>
            )}
          </GoogleMap>
        </LoadScript>
      </div>
    </div>
  )
}
