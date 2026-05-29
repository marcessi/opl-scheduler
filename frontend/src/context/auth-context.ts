import { createContext } from 'react'
import type { User } from '../api/types'

export interface AuthContextValue {
  user: User | null
  login(username: string, password: string): Promise<void>
  logout(): void
  isLoading: boolean
}

export const AuthContext = createContext<AuthContextValue | null>(null)
