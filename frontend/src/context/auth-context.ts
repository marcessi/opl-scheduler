import { createContext } from 'react'
import type { User } from '../api/types'

/** Valor del contexto de autenticación: usuario actual y acciones de sesión. */
export interface AuthContextValue {
  /** Usuario autenticado, o `null` si no hay sesión. */
  user: User | null
  /** Inicia sesión con credenciales y persiste el token. */
  login(username: string, password: string): Promise<void>
  /** Cierra la sesión y elimina el token. */
  logout(): void
  /** `true` mientras se resuelve la sesión inicial desde el token guardado. */
  isLoading: boolean
}

/** Contexto de autenticación; `null` fuera de `AuthProvider` (ver {@link useAuth}). */
export const AuthContext = createContext<AuthContextValue | null>(null)
