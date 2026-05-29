import { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/useAuth'

export default function RutaProtegida({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) return <div>Cargando...</div>

  return user ? children : <Navigate to="/login" replace />
}
