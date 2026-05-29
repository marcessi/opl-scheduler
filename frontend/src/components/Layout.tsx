import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/useAuth'
import { useSolver } from '../context/useSolver'

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const { activo, estado } = useSolver()
  const navigate = useNavigate()
  const location = useLocation()
  const [ahoraSeg, setAhoraSeg] = useState(() => Math.floor(Date.now() / 1000))

  useEffect(() => {
    if (!activo) return
    const id = window.setInterval(() => setAhoraSeg(Math.floor(Date.now() / 1000)), 1000)
    return () => window.clearInterval(id)
  }, [activo])

  const minutosTranscurridos = estado.inicio_ts
    ? Math.max(0, Math.floor((ahoraSeg - estado.inicio_ts) / 60))
    : 0
  const enRepartoEnCurso = !!estado.semana_en_curso
    && location.pathname === `/repartos/${estado.semana_en_curso}`
  const mostrarBanner = activo && !!estado.semana_en_curso && !enRepartoEnCurso

  return (
    <div className="app-shell">
      {mostrarBanner && (
        <div
          className="solver-banner"
          role="status"
          onClick={() => navigate(`/repartos/${estado.semana_en_curso}`)}
          style={{
            cursor: 'pointer',
            background: '#fff7e6',
            borderBottom: '1px solid #f0c97f',
            color: '#7a4b00',
            padding: '8px 16px',
            fontSize: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <span
            className="exec-pulse"
            style={{ background: '#f0a020' }}
          />
          <strong>Optimizando semana {estado.semana_en_curso}</strong>
          {estado.fase && <span>· Fase {estado.fase}</span>}
          {estado.inicio_ts && <span>· {minutosTranscurridos} min</span>}
          <span style={{ marginLeft: 'auto', textDecoration: 'underline' }}>
            Ver progreso
          </span>
        </div>
      )}
      <header className="topbar">
        <div className="topbar-brand">
          <img src="/marset-logo.svg" alt="Marset" className="topbar-logo-img" />
        </div>
        <div className="topbar-divider" />
        <nav className="topbar-nav">
          <NavLink
            to="/dashboard"
            className={({ isActive }) => 'topbar-link' + (isActive ? ' active' : '')}
          >
            Inicio
          </NavLink>
          <NavLink
            to="/datos-maestros"
            className={({ isActive }) => 'topbar-link' + (isActive ? ' active' : '')}
          >
            Datos
          </NavLink>
          <NavLink
            to="/repartos"
            className={({ isActive }) => 'topbar-link' + (isActive ? ' active' : '')}
          >
            Repartos
          </NavLink>
        </nav>
        <div className="topbar-spacer" />
        <div className="topbar-user">
          <span className="topbar-username">{user?.username}</span>
          <button className="btn-ghost topbar-logout" onClick={logout} aria-label="Cerrar sesión">
            Salir
          </button>
        </div>
      </header>
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}
