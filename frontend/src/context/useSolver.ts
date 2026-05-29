import { useContext } from 'react'
import { SolverContext, type SolverContextValue } from './solver-context'

export function useSolver(): SolverContextValue {
  return useContext(SolverContext)
}
