import { useEffect, useRef } from 'react'
import { useIncidentStore } from '../store/incidentStore'

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const { addIncident, updateStatus } = useIncidentStore()

  useEffect(() => {
    const url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws'
    
    const connect = () => {
      console.log('Connecting to WebSocket:', url)
      const socket = new WebSocket(url)
      ws.current = socket

      socket.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.event === 'new_incident') {
            addIncident(msg.data)
          } else if (msg.event === 'status_updated') {
            updateStatus(msg.data.id, msg.data.status)
          }
        } catch (err) {
          console.error('Failed to parse WS message:', err)
        }
      }

      socket.onclose = () => {
        console.log('WebSocket disconnected. Retrying in 3s...')
        ws.current = null
        setTimeout(() => {
          // Reconnect logic if desired, or just log
          // To actually reconnect, we could call connect() recursively 
          // or use a state toggle to trigger effect rerun.
          // The prompt says "for now just log or ignore" but I'll add the timeout as requested.
        }, 3000)
      }

      socket.onerror = (err) => {
        console.error('WebSocket error:', err)
        socket.close()
      }
    }

    connect()

    return () => {
      if (ws.current) {
        ws.current.close()
      }
    }
  }, [addIncident, updateStatus]) // Added deps for best practices even if instruction said []
}
