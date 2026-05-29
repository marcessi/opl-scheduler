import { createContext } from 'react'
import type { EstadoOptimizacionOut } from '../api/types'

export interface SolverContextValue {
  activo: boolean
  estado: EstadoOptimizacionOut
  refrescar: () => void
}

export const SolverContext = createContext<SolverContextValue>({
  activo: false,
  estado: { semana_en_curso: null, fase: null, estado: null, inicio_ts: null, n_opls: null },
  refrescar: () => {},
})
