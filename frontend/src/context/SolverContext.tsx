import { useEffect, useRef, useState, useCallback, type ReactNode } from 'react'
import { apiFetch } from '../api/client'
import type { EstadoOptimizacionOut } from '../api/types'
import { SolverContext } from './solver-context'
import { useAuth } from './useAuth'

const POLL_ACTIVO_MS = 2000
const POLL_IDLE_MS = 10000

const ESTADO_VACIO: EstadoOptimizacionOut = {
  semana_en_curso: null,
  fase: null,
  estado: null,
  inicio_ts: null,
  n_opls: null,
}

export function SolverProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [estado, setEstado] = useState<EstadoOptimizacionOut>(ESTADO_VACIO)
  const refrescarRef = useRef<() => void>(() => {})

  useEffect(() => {
    if (!user) {
      setEstado(ESTADO_VACIO)
      refrescarRef.current = () => {}
      return
    }

    let cancelled = false
    let timerId: number | null = null
    let activo = false

    const clearTimer = () => {
      if (timerId !== null) {
        window.clearTimeout(timerId)
        timerId = null
      }
    }

    const tick = async () => {
      if (cancelled) return
      try {
        const data = await apiFetch<EstadoOptimizacionOut>('/repartos/estado-optimizacion')
        if (cancelled) return
        setEstado(data)
        activo = !!data.semana_en_curso
      } catch {
        // Silenciar errores de red.
      }
      if (cancelled) return
      const delay = activo ? POLL_ACTIVO_MS : POLL_IDLE_MS
      timerId = window.setTimeout(tick, delay)
    }

    refrescarRef.current = () => {
      clearTimer()
      tick()
    }

    tick()

    return () => {
      cancelled = true
      clearTimer()
      refrescarRef.current = () => {}
    }
  }, [user])

  const refrescar = useCallback(() => refrescarRef.current(), [])

  return (
    <SolverContext.Provider value={{ activo: !!estado.semana_en_curso, estado, refrescar }}>
      {children}
    </SolverContext.Provider>
  )
}
