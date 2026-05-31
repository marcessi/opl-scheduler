import { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/useAuth'

/**
 * Guarda de ruta: exige sesión iniciada para renderizar su contenido.
 *
 * Muestra un cargando mientras se resuelve la sesión y redirige a `/login` si no
 * hay usuario autenticado.
 * @param children Contenido protegido.
 */
export default function RutaProtegida({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) return <div>Cargando...</div>

  return user ? children : <Navigate to="/login" replace />
}
