import { createContext } from 'react'
import type { EstadoOptimizacionOut } from '../api/types'

/** Valor del contexto del solver: estado global de la optimización en curso. */
export interface SolverContextValue {
  /** `true` si hay una optimización ejecutándose en alguna semana. */
  activo: boolean
  /** Último estado conocido del solver (semana, fase, ...). */
  estado: EstadoOptimizacionOut
  /** Fuerza un refresco inmediato del estado (reinicia el polling). */
  refrescar: () => void
}

export const SolverContext = createContext<SolverContextValue>({
  activo: false,
  estado: { semana_en_curso: null, fase: null, estado: null, inicio_ts: null, n_opls: null },
  refrescar: () => {},
})
