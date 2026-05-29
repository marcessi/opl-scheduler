import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { formatFechaES, formatSemanaLabel, getTodayMondayISO } from '../utils/semana'
import ResumenReparto from './repartos/ResumenReparto'
import type {
  EstadoOptimizacionOut,
  OperarioOut,
  OplOut,
  RepartoDetalleOut,
  RepartoResumenOut,
} from '../api/types'

/* ── Iconos ──────────────────────────────────────────────────── */
function Icon({ paths, size = 20 }: { paths: ReactNode; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths}
    </svg>
  )
}
const IconCalendarPlus = <Icon paths={<><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="3" y1="10" x2="21" y2="10" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="12" y1="14" x2="12" y2="18" /><line x1="10" y1="16" x2="14" y2="16" /></>} />
const IconCheck = <Icon paths={<><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.5 2.5 4.5-5" /></>} />
const IconBolt = <Icon paths={<polygon points="13 2 4 14 11 14 10 22 20 9 13 9 13 2" />} />
const IconBox = <Icon size={16} paths={<><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><path d="M3.3 7L12 12l8.7-5M12 22V12" /></>} />
const IconUsers = <Icon size={16} paths={<><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>} />
const IconPieChart = <Icon size={16} paths={<><path d="M21.21 15.89A10 10 0 1 1 8 2.83" /><path d="M22 12A10 10 0 0 0 12 2v10z" /></>} />

/* ── Modos de ejecución ──────────────────────────────────────── */
interface ModoInfo { key: string; label: string; color: string }
const MODOS: ModoInfo[] = [
  { key: 'produccion', label: 'Producción', color: '#f59e0b' },
  { key: 'balanceado', label: 'Balanceado', color: '#2563eb' },
  { key: 'personas',   label: 'Personas',   color: '#16a34a' },
]

function ModosDonut({ repartos }: { repartos: RepartoResumenOut[] }) {
  const counts = MODOS.map(m => ({ ...m, n: repartos.filter(r => r.perfil === m.key).length }))
  const total = counts.reduce((s, c) => s + c.n, 0)

  if (total === 0) {
    return (
      <>
        <div className="kpi-value">—</div>
        <div className="kpi-sub">Aún no hay ejecuciones registradas por modo.</div>
      </>
    )
  }

  // Donut SVG: circunferencia ≈ 100 (r = 15.915) → dasharray en % directo.
  const activos = counts.filter(c => c.n > 0)
  const segments = activos.map((c, i) => {
    const pct = (c.n / total) * 100
    const previo = activos.slice(0, i).reduce((s, x) => s + (x.n / total) * 100, 0)
    return { color: c.color, pct, offset: 25 - previo }
  })

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 4 }}>
      <svg width={88} height={88} viewBox="0 0 36 36" style={{ flexShrink: 0 }} aria-hidden="true">
        <circle cx="18" cy="18" r="15.915" fill="none" stroke="var(--border)" strokeWidth="4" />
        {segments.map((s, i) => (
          <circle
            key={i}
            cx="18" cy="18" r="15.915"
            fill="none"
            stroke={s.color}
            strokeWidth="4"
            strokeDasharray={`${s.pct} ${100 - s.pct}`}
            strokeDashoffset={s.offset}
          />
        ))}
        <text x="18" y="18.5" textAnchor="middle" dominantBaseline="middle"
          style={{ fontSize: 8, fontWeight: 700, fill: 'var(--text)' }}>{total}</text>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
        {counts.map(c => (
          <span key={c.key} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, color: 'var(--text)' }}>
            <span style={{
              width: 10, height: 10, borderRadius: 3, flexShrink: 0,
              background: c.n > 0 ? c.color : 'var(--border)',
            }} />
            <span style={{ color: c.n > 0 ? 'var(--text)' : 'var(--text-muted)' }}>{c.label}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

/* ── Panel de acción / próximo paso ──────────────────────────── */
interface ActionPanelModel {
  variant: 'action' | 'ok' | 'live'
  icon: ReactNode
  title: string
  desc: ReactNode
  cta?: { label: string; onClick: () => void }
}

function buildActionPanel(
  ultimo: RepartoResumenOut,
  estadoOptim: EstadoOptimizacionOut | null,
  navigate: (to: string) => void,
): ActionPanelModel {
  const hoy = getTodayMondayISO()

  if (estadoOptim?.semana_en_curso) {
    const sem = estadoOptim.semana_en_curso
    return {
      variant: 'live',
      icon: IconBolt,
      title: 'Optimización en curso',
      desc: <>Resolviendo la <strong>{formatSemanaLabel(sem)}</strong>. El resto de semanas se desbloqueará al terminar.</>,
      cta: { label: 'Ver progreso', onClick: () => navigate(`/repartos/${sem}`) },
    }
  }

  if (ultimo.semana < hoy) {
    if (!ultimo.aprobado) {
      return {
        variant: 'action',
        icon: IconCalendarPlus,
        title: 'Planifica la semana actual',
        desc: <>El último reparto (<strong>{formatSemanaLabel(ultimo.semana)}</strong>) sigue pendiente. Apruébalo y crea el reparto de la semana del <strong>{formatFechaES(hoy)}</strong>.</>,
        cta: { label: 'Ir al calendario', onClick: () => navigate('/repartos') },
      }
    }
    return {
      variant: 'action',
      icon: IconCalendarPlus,
      title: 'Crea el reparto de esta semana',
      desc: <>El último reparto aprobado fue la <strong>{formatSemanaLabel(ultimo.semana)}</strong>. Aún no hay reparto para la semana del <strong>{formatFechaES(hoy)}</strong>.</>,
      cta: { label: 'Planificar', onClick: () => navigate('/repartos') },
    }
  }

  if (ultimo.semana === hoy) {
    if (!ultimo.aprobado) {
      return {
        variant: 'action',
        icon: IconCalendarPlus,
        title: 'Continúa la planificación',
        desc: <>El reparto de la semana actual está en marcha pero <strong>sin aprobar</strong>.</>,
        cta: { label: 'Abrir reparto', onClick: () => navigate(`/repartos/${ultimo.semana}`) },
      }
    }
    return {
      variant: 'ok',
      icon: IconCheck,
      title: 'Semana al día',
      desc: <>El reparto de la semana actual (<strong>{formatSemanaLabel(ultimo.semana)}</strong>) está aprobado.</>,
    }
  }

  // ultimo.semana > hoy
  if (!ultimo.aprobado) {
    return {
      variant: 'action',
      icon: IconCalendarPlus,
      title: 'Reparto futuro pendiente',
      desc: <>Hay un reparto para la <strong>{formatSemanaLabel(ultimo.semana)}</strong> sin aprobar.</>,
      cta: { label: 'Abrir reparto', onClick: () => navigate(`/repartos/${ultimo.semana}`) },
    }
  }
  return {
    variant: 'ok',
    icon: IconCheck,
    title: 'Planificación adelantada',
    desc: <>El próximo reparto (<strong>{formatSemanaLabel(ultimo.semana)}</strong>) ya está aprobado.</>,
  }
}

function ActionPanel({ model }: { model: ActionPanelModel }) {
  return (
    <div className={`action-panel action-panel--${model.variant}`}>
      <div className="action-icon">{model.icon}</div>
      <div className="action-body">
        <div className="action-title">{model.title}</div>
        <div className="action-desc">{model.desc}</div>
      </div>
      {model.cta && (
        <div className="action-cta">
          <button className="btn-primary" onClick={model.cta.onClick}>{model.cta.label}</button>
        </div>
      )}
    </div>
  )
}

/* ── KPIs ────────────────────────────────────────────────────── */
function KpiCard({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="kpi-card">
      <div className="kpi-head">
        <span className="kpi-head-icon">{icon}</span>
        <span className="kpi-label">{label}</span>
      </div>
      {children}
    </div>
  )
}

function KpiRow({ opls, operarios, repartos }: {
  opls: OplOut[] | null
  operarios: OperarioOut[] | null
  repartos: RepartoResumenOut[]
}) {
  const totalOpls = opls?.length ?? 0
  const asignadas = opls?.filter(o => o.asignado_a).length ?? 0
  const sinAsignar = totalOpls - asignadas
  const pctAsig = totalOpls > 0 ? Math.round((asignadas / totalOpls) * 100) : 0

  const totalOperarios = operarios?.length ?? 0
  const disponibles = operarios?.filter(o => o.horas_semanales > 0).length ?? 0
  const totalHoras = operarios?.reduce((s, o) => s + o.horas_semanales, 0) ?? 0

  return (
    <div className="kpi-grid">
      <KpiCard icon={IconBox} label="OPLs sin asignar">
        {totalOpls > 0 ? (
          <>
            <div className="kpi-value">{sinAsignar}</div>
            <div className="kpi-bar kpi-bar--lg">
              <div className="kpi-bar-fill kpi-bar-fill--brand" style={{ width: `${pctAsig}%` }} />
            </div>
            <div className="kpi-legend">
              <span className="kpi-legend-item">
                <span className="kpi-dot" style={{ background: 'var(--brand)' }} /> Asignadas
              </span>
              <span className="kpi-legend-item">
                <span className="kpi-dot" style={{ background: 'var(--border)' }} /> Sin asignar
              </span>
            </div>
            {sinAsignar === 0 && (
              <div className="kpi-sub"><span className="kpi-flag kpi-flag--ok">Todo planificado</span></div>
            )}
          </>
        ) : (
          <>
            <div className="kpi-value">—</div>
            <div className="kpi-sub"><span className="kpi-flag kpi-flag--warn">Sin OPLs · importa datos</span></div>
          </>
        )}
      </KpiCard>

      <KpiCard icon={IconUsers} label="Operarios disponibles">
        <div className="kpi-value">{disponibles}<span className="kpi-value-unit"> / {totalOperarios}</span></div>
        <div className="kpi-sub">
          <strong>{totalHoras}</strong> h/semana disponibles
        </div>
      </KpiCard>

      <KpiCard icon={IconPieChart} label="Modos de ejecución">
        <ModosDonut repartos={repartos} />
      </KpiCard>
    </div>
  )
}

/* ── Lista de repartos recientes ─────────────────────────────── */
function Badge({ aprobado }: { aprobado: boolean }) {
  return (
    <span className={aprobado ? 'badge badge-ok' : 'badge badge-pending'}>
      {aprobado ? 'Aprobado' : 'Pendiente'}
    </span>
  )
}

function RepartosRecientes({ repartos, onRowClick }: { repartos: RepartoResumenOut[]; onRowClick: (semana: string) => void }) {
  if (repartos.length === 0) return null

  return (
    <div>
      <div className="dash-section-label">Repartos recientes</div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Semana</th>
              <th>Estado</th>
              <th>Asignadas</th>
              <th>Pendientes</th>
            </tr>
          </thead>
          <tbody>
            {repartos.map(r => (
              <tr key={r.semana} className="table-row-link" onClick={() => onRowClick(r.semana)}>
                <td>{formatSemanaLabel(r.semana)}</td>
                <td><Badge aprobado={r.aprobado} /></td>
                <td>{r.n_asignadas}</td>
                <td>{r.n_pendientes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ── Página ──────────────────────────────────────────────────── */
export default function Dashboard() {
  const [repartos, setRepartos] = useState<RepartoResumenOut[] | null>(null)
  const [estadoOptim, setEstadoOptim] = useState<EstadoOptimizacionOut | null>(null)
  const [opls, setOpls] = useState<OplOut[] | null>(null)
  const [operarios, setOperarios] = useState<OperarioOut[] | null>(null)
  const [ultimoDetalle, setUltimoDetalle] = useState<RepartoDetalleOut | null>(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    let cancel = false
    async function load() {
      try {
        const [reps, est, oplList, ops] = await Promise.all([
          apiFetch<RepartoResumenOut[]>('/repartos'),
          apiFetch<EstadoOptimizacionOut>('/repartos/estado-optimizacion').catch(() => null),
          apiFetch<OplOut[]>('/opls').catch(() => null),
          apiFetch<OperarioOut[]>('/operarios').catch(() => null),
        ])
        if (cancel) return
        const ordenados = [...reps].sort((a, b) => b.semana.localeCompare(a.semana))
        setRepartos(ordenados)
        setEstadoOptim(est)
        setOpls(oplList)
        setOperarios(ops)

        const ultimo = ordenados[0]
        if (ultimo) {
          const det = await apiFetch<RepartoDetalleOut>(`/repartos/${ultimo.semana}`).catch(() => null)
          if (!cancel) setUltimoDetalle(det)
        }
      } catch (err) {
        if (!cancel) setError(err instanceof Error ? err.message : 'Error')
      }
    }
    void load()
    const id = setInterval(() => {
      apiFetch<EstadoOptimizacionOut>('/repartos/estado-optimizacion')
        .then(est => { if (!cancel) setEstadoOptim(est) })
        .catch(() => {})
    }, 5000)
    return () => { cancel = true; clearInterval(id) }
  }, [])

  if (error) return (
    <>
      <h1 className="page-title">Dashboard</h1>
      <p className="error-msg">{error}</p>
    </>
  )

  if (repartos === null) return (
    <>
      <h1 className="page-title">Dashboard</h1>
      <p style={{ color: 'var(--text-muted)' }}>Cargando...</p>
    </>
  )

  if (repartos.length === 0) return (
    <>
      <h1 className="page-title">Dashboard</h1>
      <div className="empty-state">
        <div className="empty-state-title">Sin repartos aún</div>
        <p>Importa los datos e inicia una optimización para ver los resultados aquí.</p>
      </div>
    </>
  )

  const ultimo = repartos[0]!
  const anteriores = repartos.slice(1)
  const actionModel = buildActionPanel(ultimo, estadoOptim, navigate)

  return (
    <>
      <h1 className="page-title">Dashboard</h1>
      <div className="dashboard-grid">
        <div>
          <div className="dash-section-label">Estado general</div>
          <KpiRow opls={opls} operarios={operarios} repartos={repartos} />
        </div>

        <div>
          <div className="dash-section-label">Próximo paso</div>
          <ActionPanel model={actionModel} />
        </div>

        {ultimoDetalle && operarios && (
          <div>
            <div className="dash-section-label">Último reparto</div>
            <ResumenReparto
              semana={ultimo.semana}
              isAprobado={ultimo.aprobado}
              reparto={ultimoDetalle}
              operarios={operarios}
              resultado={null}
              optimizeError=""
            />
          </div>
        )}

        <RepartosRecientes repartos={anteriores.slice(0, 6)} onRowClick={(semana) => navigate(`/repartos/${semana}`)} />
      </div>
    </>
  )
}
