import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { addDaysToISO, formatFechaES, getTodayMondayISO, getWeeksForMonth, toISODate } from '../utils/semana'
import type { EstadoOptimizacionOut, RepartoDetalleOut, RepartoResumenOut } from '../api/types'

const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]
const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

interface MonthPickerProps {
  year: number
  month: number
  onSelect: (year: number, month: number) => void
  onClose: () => void
}

function MonthPicker({ year, month, onSelect, onClose }: MonthPickerProps) {
  const [pickerYear, setPickerYear] = useState(year)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [onClose])

  return (
    <div className="mp-overlay" ref={ref}>
      <div className="mp-header">
        <button className="btn-ghost" onClick={() => setPickerYear(y => y - 1)}>&#8592;</button>
        <span className="mp-year">{pickerYear}</span>
        <button className="btn-ghost" onClick={() => setPickerYear(y => y + 1)}>&#8594;</button>
      </div>
      <div className="mp-grid">
        {MESES.map((name, i) => (
          <button
            key={i}
            className={'mp-month' + (i === month && pickerYear === year ? ' mp-month--active' : '')}
            onClick={() => { onSelect(pickerYear, i); onClose() }}
          >
            {name.slice(0, 3)}
          </button>
        ))}
      </div>
    </div>
  )
}

interface ResolverContext {
  bloqueada: string
  destino: string
  obligatoriasPendientes: number
}

type ApproveStep = 'warning' | 'select'
type ArrastreOption = 'none' | 'parciales' | 'todas'

interface ApproveState {
  step: ApproveStep
  option: ArrastreOption
}

interface ResolverSemanaModalProps {
  bloqueada: string | undefined
  destino: string | undefined
  obligatoriasPendientes: number
  loading: boolean
  error: string
  onClose: () => void
  onResolver: (opts: { conArrastre: boolean; incluirNoAsignadas: boolean }) => void
}

const ARRASTRE_OPTIONS: { id: ArrastreOption; label: string; desc: (destino: string) => string; icon: string; recomendado?: boolean }[] = [
  {
    id: 'todas',
    label: 'Parciales y sin asignar',
    desc: (destino) => `Las OPLs parciales y las que no se han podido asignar pasan como obligatorias a ${destino}.`,
    icon: '⇉',
    recomendado: true,
  },
  {
    id: 'parciales',
    label: 'Solo OPLs parciales',
    desc: (destino) => `Las OPLs que no dio tiempo a completar esta semana pasan a ${destino}.`,
    icon: '◐',
  },
  {
    id: 'none',
    label: 'Ninguna',
    desc: (destino) => `Se aprueba la semana actual sin generar pendientes en ${destino}.`,
    icon: '—',
  },
]

function ResolverSemanaModal({ bloqueada, destino, obligatoriasPendientes, loading, error, onClose, onResolver }: ResolverSemanaModalProps) {
  const [state, setState] = useState<ApproveState>({
    step: obligatoriasPendientes > 0 ? 'warning' : 'select',
    option: 'todas',
  })

  useEffect(() => {
    setState({ step: obligatoriasPendientes > 0 ? 'warning' : 'select', option: 'todas' })
  }, [bloqueada, destino, obligatoriasPendientes])

  if (!bloqueada || !destino) return null

  const isWarning = state.step === 'warning'
  const isSelect = state.step === 'select'

  function handleAprobar() {
    onResolver({
      conArrastre: state.option !== 'none',
      incluirNoAsignadas: state.option === 'todas',
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">
            {isWarning ? 'OPLs obligatorias pendientes' : `Aprobar semana ${formatFechaES(bloqueada)}`}
          </span>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">×</button>
        </div>
        <div className="modal-body">
          {isWarning && (
            <div className="approve-warning-box">
              <span className="approve-warning-icon">⚠</span>
              <p style={{ margin: 0 }}>
                La semana <strong>{formatFechaES(bloqueada)}</strong> tiene{' '}
                <strong>{obligatoriasPendientes}</strong>{' '}
                {obligatoriasPendientes === 1 ? 'OPL obligatoria sin asignar' : 'OPLs obligatorias sin asignar'}.
                Si continúa, aprobará la semana con {obligatoriasPendientes === 1 ? 'esta OPL pendiente' : 'estas OPLs pendientes'}.
              </p>
            </div>
          )}
          {isSelect && (
            <>
              <p className="approve-subtitle">
                Selecciona qué OPLs se arrastran a la semana <strong>{formatFechaES(destino)}</strong>.
              </p>
              <div className="option-card-group" role="radiogroup">
                {ARRASTRE_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    className={'option-card' + (state.option === opt.id ? ' option-card--selected' : '')}
                    onClick={() => setState((s) => ({ ...s, option: opt.id }))}
                    disabled={loading}
                    type="button"
                    role="radio"
                    aria-checked={state.option === opt.id}
                  >
                    <span className="option-card-icon" aria-hidden="true">{opt.icon}</span>
                    <span className="option-card-content">
                      <span className="option-card-label">
                        {opt.label}
                        {opt.recomendado && <span className="option-card-badge">Por defecto</span>}
                      </span>
                      <span className="option-card-desc">{opt.desc(formatFechaES(destino))}</span>
                    </span>
                    <span className="option-card-radio" />
                  </button>
                ))}
              </div>
            </>
          )}
          {error && <p className="error-msg" style={{ marginTop: '12px' }}>{error}</p>}
        </div>
        <div className="modal-footer">
          <button className="btn-ghost" onClick={onClose} disabled={loading}>Cancelar</button>
          {isWarning && (
            <button
              className="btn-primary"
              style={{ width: 'auto' }}
              onClick={() => setState((s) => ({ ...s, step: 'select' }))}
              disabled={loading}
            >
              Continuar
            </button>
          )}
          {isSelect && (
            <button
              className="btn-primary"
              style={{ width: 'auto' }}
              onClick={handleAprobar}
              disabled={loading}
            >
              {loading ? 'Procesando...' : 'Aprobar semana'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/** Página de listado de repartos: muestra los repartos existentes y permite crear/abrir una semana. */
export default function Repartos() {
  const [repartos, setRepartos] = useState<RepartoResumenOut[] | null>(null)
  const [error, setError] = useState('')
  const [viewDate, setViewDate] = useState(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1)
  })
  const [pickerOpen, setPickerOpen] = useState(false)
  const [creationMessage, setCreationMessage] = useState('')
  const [resolverContext, setResolverContext] = useState<ResolverContext | null>(null)
  const [resolverLoading, setResolverLoading] = useState(false)
  const [resolverError, setResolverError] = useState('')
  const [highlightMonday, setHighlightMonday] = useState<string | null>(null)
  const [highlightKey, setHighlightKey] = useState(0)
  const [semanaEnCurso, setSemanaEnCurso] = useState<string | null>(null)
  const highlightTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const navigate = useNavigate()

  async function cargarRepartos() {
    try {
      const data = await apiFetch<RepartoResumenOut[]>('/repartos')
      setRepartos(data)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error')
    }
  }

  async function cargarEstadoOptimizacion() {
    try {
      const data = await apiFetch<EstadoOptimizacionOut>('/repartos/estado-optimizacion')
      setSemanaEnCurso(data.semana_en_curso)
    } catch {
      // silencioso: no debe romper la página si el endpoint falla puntualmente
    }
  }

  useEffect(() => {
    void cargarRepartos()
  }, [])

  useEffect(() => {
    void cargarEstadoOptimizacion()
    const id = setInterval(() => { void cargarEstadoOptimizacion() }, 5000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    return () => {
      if (highlightTimer.current) clearTimeout(highlightTimer.current)
    }
  }, [])

  const repartoMap = repartos
    ? new Map(repartos.map(r => [r.semana, r]))
    : null

  const semanasOrdenadas = repartos
    ? [...new Set(repartos.map(r => r.semana))].sort()
    : []
  const ultimaSemanaExistente = semanasOrdenadas.length > 0 ? semanasOrdenadas[semanasOrdenadas.length - 1] ?? null : null
  const todosAprobados = repartos ? repartos.every(r => r.aprobado) : true

  const { minimoFuturoSeleccionable, primerPendiente } = (() => {
    if (!repartos || repartos.length === 0 || !ultimaSemanaExistente) {
      return {
        minimoFuturoSeleccionable: getTodayMondayISO(),
        primerPendiente: null as string | null,
      }
    }

    if (!todosAprobados) {
      const pendiente = repartos.filter(r => !r.aprobado).map(r => r.semana).sort()[0] ?? null
      return {
        minimoFuturoSeleccionable: addDaysToISO(ultimaSemanaExistente, 7),
        primerPendiente: pendiente,
      }
    }

    return {
      minimoFuturoSeleccionable: addDaysToISO(ultimaSemanaExistente, 7),
      primerPendiente: null as string | null,
    }
  })()

  function ultimaAnteriorExistente(semana: string): string | null {
    let prev: string | null = null
    for (const s of semanasOrdenadas) {
      if (s < semana) prev = s
      else break
    }
    return prev
  }

  async function abrirSemana(mondayISO: string) {
    setCreationMessage('')

    const existente = repartoMap?.get(mondayISO)
    if (existente) {
      navigate(`/repartos/${mondayISO}`)
      return
    }

    if (ultimaSemanaExistente && mondayISO <= ultimaSemanaExistente) {
      setCreationMessage(`No puedes crear un reparto en ${formatFechaES(mondayISO)}: solo se permiten semanas futuras.`)
      return
    }

    if (!ultimaSemanaExistente && mondayISO < minimoFuturoSeleccionable) {
      setCreationMessage(`No puedes crear un reparto en ${formatFechaES(mondayISO)}: solo se permiten semanas desde ${formatFechaES(minimoFuturoSeleccionable)}.`)
      return
    }

    const anterior = ultimaAnteriorExistente(mondayISO)
    const anteriorReparto = anterior ? repartoMap?.get(anterior) : null
    if (anteriorReparto && !anteriorReparto.aprobado) {
      setResolverError('')
      try {
        const detalle = await apiFetch<RepartoDetalleOut>(`/repartos/${anteriorReparto.semana}`)
        const obligatoriasPendientes = (detalle.asignaciones ?? []).filter(
          a => a.tipo_asignacion === 'obligatoria' && !a.es_fija && !a.dni_operario
        ).length
        setResolverContext({
          bloqueada: anteriorReparto.semana,
          destino: mondayISO,
          obligatoriasPendientes,
        })
      } catch (err) {
        setCreationMessage(err instanceof Error ? err.message : 'Error')
      }
      return
    }

    navigate(`/repartos/${mondayISO}`)
  }

  async function resolverSemanaBloqueada(opts: { conArrastre: boolean; incluirNoAsignadas: boolean }) {
    if (!resolverContext) return

    setResolverLoading(true)
    setResolverError('')
    const { bloqueada, destino } = resolverContext
    try {
      await apiFetch<unknown>(`/repartos/${bloqueada}/aprobar`, {
        method: 'POST',
        body: JSON.stringify({
          semana_destino: destino,
          con_arrastre: opts.conArrastre,
          incluir_no_asignadas_en_arrastre: opts.incluirNoAsignadas,
          forzar_obligatorias_pendientes: resolverContext.obligatoriasPendientes > 0,
        }),
      })

      await cargarRepartos()
      setResolverContext(null)
      navigate(`/repartos/${destino}`)
    } catch (err) {
      setResolverError(err instanceof Error ? err.message : 'Error')
    } finally {
      setResolverLoading(false)
    }
  }

  function prevMonth() {
    setViewDate(d => new Date(d.getFullYear(), d.getMonth() - 1, 1))
  }
  function nextMonth() {
    setViewDate(d => new Date(d.getFullYear(), d.getMonth() + 1, 1))
  }
  function goToToday() {
    const now = new Date()
    setViewDate(new Date(now.getFullYear(), now.getMonth(), 1))
    const monday = getTodayMondayISO()
    if (highlightTimer.current) clearTimeout(highlightTimer.current)
    setHighlightKey(k => k + 1)
    setHighlightMonday(monday)
    highlightTimer.current = setTimeout(() => setHighlightMonday(null), 1200)
  }

  const weeks = getWeeksForMonth(viewDate.getFullYear(), viewDate.getMonth())
  const currentMonth = viewDate.getMonth()

  if (error) return (
    <>
      <h1 className="page-title">Repartos</h1>
      <p className="error-msg">{error}</p>
    </>
  )

  if (repartos === null) return (
    <>
      <h1 className="page-title">Repartos</h1>
      <p style={{ color: 'var(--text-muted)' }}>Cargando...</p>
    </>
  )

  return (
    <>
      <h1 className="page-title">Repartos</h1>

      <div className="cal-toolbar">
        <div className="cal-nav">
          <button className="btn-ghost" onClick={prevMonth}>&#8592;</button>
          <div className="cal-nav-title-wrap">
            <button
              className="cal-nav-title"
              onClick={() => setPickerOpen(o => !o)}
              aria-expanded={pickerOpen}
              aria-label="Seleccionar mes"
            >
              {MESES[viewDate.getMonth()]} {viewDate.getFullYear()}
            </button>
            {pickerOpen && (
              <MonthPicker
                year={viewDate.getFullYear()}
                month={viewDate.getMonth()}
                onSelect={(y, m) => setViewDate(new Date(y, m, 1))}
                onClose={() => setPickerOpen(false)}
              />
            )}
          </div>
          <button className="btn-ghost" onClick={nextMonth}>&#8594;</button>
        </div>
        <button className="btn-ghost" onClick={goToToday} title="Ir a la semana actual">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
            <circle cx="12" cy="16" r="2"/>
          </svg>
        </button>
      </div>

      <div className="card cal-card">
        <table className="cal-table">
          <thead>
            <tr>
              {DIAS.map(d => <th key={d} className="cal-th">{d}</th>)}
            </tr>
          </thead>
          <tbody>
            {weeks.map(week => {
              const mondayISO = toISODate(week.monday)
              const reparto = repartoMap?.get(mondayISO) ?? null

              const esFutura = !reparto && (
                (ultimaSemanaExistente && mondayISO > ultimaSemanaExistente) ||
                (!ultimaSemanaExistente && mondayISO >= minimoFuturoSeleccionable)
              )
              const bloqueadaPorOptim = semanaEnCurso !== null && mondayISO > semanaEnCurso
              const navegable = !bloqueadaPorOptim && (reparto || esFutura)

              let rowClass = 'cal-row cal-row--none'
              if (reparto) {
                rowClass = reparto.aprobado ? 'cal-row cal-row--aprobado' : 'cal-row cal-row--pendiente'
              } else if (esFutura) {
                rowClass = 'cal-row cal-row--none cal-row--none-action'
              }
              if (bloqueadaPorOptim) rowClass += ' cal-row--locked'
              if (highlightMonday === mondayISO) rowClass += highlightKey % 2 === 0 ? ' cal-row--hl-a' : ' cal-row--hl-b'

              return (
                <tr
                  key={mondayISO}
                  className={rowClass}
                  onClick={navegable ? () => { void abrirSemana(mondayISO) } : undefined}
                  onKeyDown={navegable ? (e) => { if (e.key === 'Enter') { void abrirSemana(mondayISO) } } : undefined}
                  tabIndex={navegable ? 0 : undefined}
                  role={navegable ? 'link' : undefined}
                >
                  {week.days.map(day => {
                    const iso = toISODate(day)
                    const isOutside = day.getMonth() !== currentMonth
                    return (
                      <td key={iso} className={'cal-td' + (isOutside ? ' cal-td--outside' : '')}>
                        {day.getDate()}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="cal-legend">
        <div className="cal-legend-item">
          <span className="cal-legend-dot" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }} />
          Sin reparto
        </div>
        <div className="cal-legend-item">
          <span className="cal-legend-dot" style={{ background: '#fef3c7', border: '1px solid #f59e0b' }} />
          Pendiente
        </div>
        <div className="cal-legend-item">
          <span className="cal-legend-dot" style={{ background: '#d1fae5', border: '1px solid #34d399' }} />
          Aprobado
        </div>
      </div>

      {(semanaEnCurso || primerPendiente || creationMessage) && (
        <div className="cal-banners">
          {semanaEnCurso && (
            <div className="cal-banner cal-banner--info">
              <span className="cal-banner-icon"><span className="cal-live-dot" /></span>
              <div className="cal-banner-body">
                <div className="cal-banner-title">Optimización en curso</div>
                <div className="cal-banner-text">
                  Resolviendo la semana <span className="cal-banner-week">{formatFechaES(semanaEnCurso)}</span>.
                  Las semanas posteriores se desbloquearán automáticamente al terminar.
                </div>
              </div>
            </div>
          )}

          {primerPendiente && (
            <div className="cal-banner cal-banner--warning">
              <span className="cal-banner-icon">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12" y2="17" />
                </svg>
              </span>
              <div className="cal-banner-body">
                <div className="cal-banner-title">Semanas pendientes de aprobar</div>
                <div className="cal-banner-text">
                  Para planificar nuevas semanas debes aprobar antes las pendientes.
                  La aprobación se hace al crear la siguiente semana en el calendario.
                  Primera bloqueante: <span className="cal-banner-week">{formatFechaES(primerPendiente)}</span>.
                </div>
              </div>
            </div>
          )}

          {creationMessage && (
            <div className="cal-banner cal-banner--error">
              <span className="cal-banner-icon">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
                </svg>
              </span>
              <div className="cal-banner-body">
                <div className="cal-banner-title">No se puede crear el reparto</div>
                <div className="cal-banner-text">{creationMessage}</div>
              </div>
            </div>
          )}
        </div>
      )}

      <ResolverSemanaModal
        bloqueada={resolverContext?.bloqueada}
        destino={resolverContext?.destino}
        obligatoriasPendientes={resolverContext?.obligatoriasPendientes ?? 0}
        loading={resolverLoading}
        error={resolverError}
        onClose={() => {
          if (resolverLoading) return
          setResolverContext(null)
          setResolverError('')
        }}
        onResolver={resolverSemanaBloqueada}
      />
    </>
  )
}
