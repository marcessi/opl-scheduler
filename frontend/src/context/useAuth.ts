import { useContext } from 'react'
import { AuthContext } from './auth-context'
import type { AuthContextValue } from './auth-context'

/**
 * Accede al contexto de autenticación.
 * @returns El valor del contexto de auth.
 * @throws {Error} Si se usa fuera de `AuthProvider`.
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export type { AuthContextValue }
