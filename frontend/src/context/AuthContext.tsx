import { useState, useEffect, type ReactNode } from 'react'
import { apiFetch } from '../api/client'
import type { User, LoginResponse } from '../api/types'
import { AuthContext } from './auth-context'

/**
 * Provider de autenticación.
 *
 * Al montar, intenta restaurar la sesión desde el JWT guardado en `localStorage`
 * y expone `login`/`logout` al árbol de componentes.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      setIsLoading(false)
      return
    }
    apiFetch<User>('/auth/me')
      .then(data => setUser(data))
      .catch(() => {
        // Token inválido o expirado — limpiar y dejar que RutaProtegida redirija
        localStorage.removeItem('jwt_token')
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  async function login(username: string, password: string): Promise<void> {
    const data = await apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    localStorage.setItem('jwt_token', data.access_token)
    const me = await apiFetch<User>('/auth/me')
    setUser(me)
  }

  function logout(): void {
    localStorage.removeItem('jwt_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}
