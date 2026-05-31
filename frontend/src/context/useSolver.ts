import { useContext } from 'react'
import { SolverContext, type SolverContextValue } from './solver-context'

/**
 * Accede al contexto del solver (estado global de la optimización).
 * @returns El valor del contexto del solver.
 */
export function useSolver(): SolverContextValue {
  return useContext(SolverContext)
}
