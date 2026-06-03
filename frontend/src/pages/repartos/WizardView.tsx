import { useEffect, useRef, useState, type ReactNode } from 'react'
import { STEPS, PERFILES, FASES_PROGRESO, TIEMPO_MIN, TIEMPO_MAX, TIEMPO_MARKS, TIEMPO_MINIMO_POR_MODO, type StepKey, type PerfilKey } from './constantes'
import { estadoBadgeClass, estadoLabel } from './utilidades'
import TablaSeleccionOpl from './TablaSeleccionOpl'
import type { OplOut, ProgresoOut } from '../../api/types'

type ArticuloMap = Map<string, string>

/* ── Iconos (lucide-style, coherentes con Dashboard) ─────────── */
function Icon({ paths, size = 20 }: { paths: ReactNode; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths}
    </svg>
  )
}
const IconBox = <Icon paths={<><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><path d="M3.3 7L12 12l8.7-5M12 22V12" /></>} />
const IconSliders = <Icon paths={<><line x1="21" y1="4" x2="14" y2="4" /><line x1="10" y1="4" x2="3" y2="4" /><line x1="21" y1="12" x2="12" y2="12" /><line x1="8" y1="12" x2="3" y2="12" /><line x1="21" y1="20" x2="16" y2="20" /><line x1="12" y1="20" x2="3" y2="20" /><line x1="14" y1="2" x2="14" y2="6" /><line x1="8" y1="10" x2="8" y2="14" /><line x1="16" y1="18" x2="16" y2="22" /></>} />
const IconBolt = <Icon paths={<polygon points="13 2 4 14 11 14 10 22 20 9 13 9 13 2" />} />
const IconScale = <Icon paths={<><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" /><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" /><path d="M7 21h10" /><path d="M12 3v18" /><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" /></>} />
const IconUsers = <Icon paths={<><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>} />
const IconClock = <Icon paths={<><circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15 14" /></>} />
const IconCheck = <Icon size={14} paths={<polyline points="20 6 9 17 4 12" />} />
const IconCheckCircle = <Icon size={14} paths={<><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.5 2.5 4.5-5" /></>} />
const IconAlert = <Icon size={14} paths={<><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>} />

const PERFIL_ICONS: Record<PerfilKey, ReactNode> = {
  produccion: IconBolt,
  balanceado: IconScale,
  personas: IconUsers,
}

/* Cabecera de paso: icono + título + descripción + acciones */
function StepHeader({ icon, title, desc, actions }: {
  icon: ReactNode
  title: string
  desc: string
  actions?: ReactNode
}) {
  return (
    <div className="wizard-step-head">
      <span className="wizard-step-head-icon">{icon}</span>
      <div className="wizard-step-head-text">
        <div className="wizard-step-head-title">{title}</div>
        <div className="wizard-step-head-desc">{desc}</div>
      </div>
      {actions && <div className="wizard-step-head-actions">{actions}</div>}
    </div>
  )
}

interface Props {
  step: StepKey
  setStep: (step: StepKey) => void
  canGoToConfig: boolean
  canGoToExec: boolean
  hasBeenOptimized: boolean
  // Step 1
  opls: OplOut[] | null
  selectedOplIds: string[]
  obligatoriaIds: string[]
  onSelectionChange: (ids: string[]) => void
  onShowPegar: () => void
  onShowManual: () => void
  articulosByRef: ArticuloMap
  // Step 2
  perfil: PerfilKey
  onPerfilChange: (key: PerfilKey) => void
  tiempoMaximoMin: number
  setTiempoMaximo: (v: number) => void
  // Step 3
  progreso: ProgresoOut | null
  optimizing: boolean
  optimizeError: string
  summaryOplCount: number
  summaryPerfilKey: PerfilKey
  summaryTiempo: string
  onEjecutar: () => void
  onCancelar: () => void
  onVolverResultados: () => void
  solverBloqueo?: boolean
}

/**
 * Asistente de optimización en 3 pasos: selección de OPLs, configuración (perfil y
 * tiempo) y ejecución con seguimiento del progreso por fases.
 *
 * Recibe todo su estado y callbacks desde {@link RepartoDetalle}; es un componente
 * controlado sin estado de negocio propio.
 */
export default function WizardView({
  step, setStep,
  canGoToConfig, canGoToExec, hasBeenOptimized,
  opls, selectedOplIds, obligatoriaIds, onSelectionChange, onShowPegar, onShowManual, articulosByRef,
  perfil, onPerfilChange,
  tiempoMaximoMin, setTiempoMaximo,
  progreso, optimizing, optimizeError,
  summaryOplCount, summaryPerfilKey, summaryTiempo,
  onEjecutar, onCancelar, onVolverResultados,
  solverBloqueo = false,
}: Props) {
  const [transcurridoSeg, setTranscurridoSeg] = useState(0)
  const [confirmandoCancelar, setConfirmandoCancelar] = useState(false)
  const [cancelando, setCancelando] = useState(false)
  const progresoRef = useRef(progreso)

  useEffect(() => {
    progresoRef.current = progreso
  })

  useEffect(() => {
    if (!optimizing) {
      setTranscurridoSeg(0)
      setConfirmandoCancelar(false)
      setCancelando(false)
      return
    }
    const inicioTs = progresoRef.current?.inicio_ts ?? null
    const offset = inicioTs !== null
      ? Math.max(0, Math.floor(Date.now() / 1000 - inicioTs))
      : 0
    setTranscurridoSeg(offset)
    const id = setInterval(() => setTranscurridoSeg(s => s + 1), 1000)
    return () => clearInterval(id)
  }, [optimizing])

  const formatoTranscurrido = `${Math.floor(transcurridoSeg / 60)}:${String(transcurridoSeg % 60).padStart(2, '0')}`
  const modoTitle = PERFILES.find(p => p.key === perfil)?.title ?? 'modo'
  const minimoModo = TIEMPO_MINIMO_POR_MODO[perfil]
  const tiempoInsuficiente = tiempoMaximoMin < minimoModo
  const pctTiempo = ((tiempoMaximoMin - TIEMPO_MIN) / (TIEMPO_MAX - TIEMPO_MIN)) * 100
  const pctMinimo = ((minimoModo - TIEMPO_MIN) / (TIEMPO_MAX - TIEMPO_MIN)) * 100
  const totalOpls = selectedOplIds.length + obligatoriaIds.length

  function handleAnterior() {
    if (step === 'config') setStep('opls')
    if (step === 'ejecucion') setStep('config')
  }

  function handleConfirmarCancelar() {
    setCancelando(true)
    setConfirmandoCancelar(false)
    onCancelar()
  }

  function handleSiguiente() {
    if (step === 'opls' && canGoToConfig) setStep('config')
    if (step === 'config' && canGoToExec) setStep('ejecucion')
  }

  const anteriorDisabled = step === 'ejecucion' && optimizing
  const siguienteDisabled =
    (step === 'opls' && !canGoToConfig) ||
    (step === 'config' && !canGoToExec)

  return (
    <div className="card wizard-card">

      {/* ── Header sticky: back · stepper · nav ── */}
      <div className="wizard-header">

        <div className="wizard-header-start">
          {hasBeenOptimized && !optimizing && (
            <button className="btn-ghost" onClick={onVolverResultados}>
              ← Ver reparto
            </button>
          )}
        </div>

        <div className="stepper wizard-stepper">
          {STEPS.map((s, i) => {
            const isActive = step === s.key
            const isDone = STEPS.findIndex(x => x.key === step) > i
            const isDisabled =
              optimizing ||
              (s.key === 'config' && !canGoToConfig) ||
              (s.key === 'ejecucion' && !canGoToExec)
            return (
              <button
                key={s.key}
                className={
                  'stepper-item' +
                  (isActive ? ' stepper-item--active' : '') +
                  (isDone ? ' stepper-item--done' : '') +
                  (isDisabled ? ' stepper-item--disabled' : '')
                }
                onClick={() => !isDisabled && setStep(s.key)}
                disabled={isDisabled}
              >
                <span className="stepper-number">{isDone ? '✓' : s.number}</span>
                <span className="stepper-label">{s.label}</span>
              </button>
            )
          })}
        </div>

        <div className="wizard-nav">
          {step !== 'opls' && (
            <button
              className="btn-ghost wizard-nav-btn"
              onClick={handleAnterior}
              disabled={anteriorDisabled}
            >
              ← Anterior
            </button>
          )}
          {step === 'ejecucion' ? (
            optimizing ? (
              confirmandoCancelar ? (
                <div className="wizard-cancel-confirm">
                  <span className="wizard-cancel-confirm-text">
                    {IconAlert} ¿Cancelar? Se perderá el progreso.
                  </span>
                  <button
                    className="btn-ghost wizard-nav-btn"
                    onClick={() => setConfirmandoCancelar(false)}
                  >
                    Seguir
                  </button>
                  <button
                    className="btn-danger wizard-nav-btn"
                    onClick={handleConfirmarCancelar}
                  >
                    Sí, cancelar
                  </button>
                </div>
              ) : (
                <div className="wizard-exec-actions">
                  <button className="btn-primary wizard-nav-btn" disabled>
                    {cancelando ? 'Cancelando…' : 'Optimizando…'}
                  </button>
                  <button
                    className="btn-danger-ghost wizard-nav-btn"
                    onClick={() => setConfirmandoCancelar(true)}
                    disabled={cancelando}
                  >
                    {cancelando ? 'Cancelando…' : 'Cancelar'}
                  </button>
                </div>
              )
            ) : (
              <button
                className="btn-primary wizard-nav-btn"
                onClick={onEjecutar}
                disabled={totalOpls === 0 || solverBloqueo}
                title={solverBloqueo ? 'Bloqueado: optimización en curso de otra semana' : undefined}
              >
                {`Ejecutar ${totalOpls} OPL${totalOpls !== 1 ? 's' : ''}`}
              </button>
            )
          ) : (
            <button
              className="btn-primary wizard-nav-btn"
              onClick={handleSiguiente}
              disabled={siguienteDisabled}
            >
              Siguiente →
            </button>
          )}
        </div>

      </div>

      {/* ── Paso 1: Selección de OPLs ── */}
      {step === 'opls' && (
        <div className="step-content">
          <StepHeader
            icon={IconBox}
            title="Selección de OPLs"
            desc="Elige las órdenes de producción a repartir esta semana"
            actions={
              <div className="section-actions">
                {selectedOplIds.length > 0 && (
                  <span className="opl-select-count">
                    <strong>{selectedOplIds.length}</strong> normal{selectedOplIds.length !== 1 ? 'es' : ''}
                  </span>
                )}
                {obligatoriaIds.length > 0 && (
                  <span className="opl-select-count opl-select-count--obligatoria">
                    <strong>{obligatoriaIds.length}</strong> obligatoria{obligatoriaIds.length !== 1 ? 's' : ''}
                  </span>
                )}
                {selectedOplIds.length === 0 && obligatoriaIds.length === 0 && (
                  <span className="opl-select-count opl-select-count--muted">0 seleccionadas</span>
                )}
                <button
                  className="btn-ghost"
                  style={{ width: 'auto' }}
                  onClick={onShowManual}
                  disabled={solverBloqueo}
                  title={solverBloqueo ? 'Bloqueado: optimización en curso' : undefined}
                >
                  Añadir OPL manual
                </button>
                <button
                  className="btn-primary"
                  style={{ width: 'auto' }}
                  onClick={onShowPegar}
                  disabled={solverBloqueo}
                  title={solverBloqueo ? 'Bloqueado: optimización en curso' : undefined}
                >
                  Pegar OPLs
                </button>
              </div>
            }
          />

          <div style={{ marginTop: '16px' }}>
            <TablaSeleccionOpl
              opls={opls}
              selectedIds={selectedOplIds}
              obligatoriaIds={obligatoriaIds}
              onChange={onSelectionChange}
              articulosByRef={articulosByRef}
            />
          </div>
        </div>
      )}

      {/* ── Paso 2: Configuración del optimizador ── */}
      {step === 'config' && (
        <div className="step-content">
          <StepHeader
            icon={IconSliders}
            title="Perfil de optimización"
            desc="Define cómo priorizar entre eficiencia y equidad"
          />

          <div className="profile-cards" style={{ marginTop: '16px' }}>
            {PERFILES.map(p => {
              const isActive = perfil === p.key
              return (
                <button
                  key={p.key}
                  type="button"
                  className={`profile-card profile-card--${p.key}` + (isActive ? ' profile-card--active' : '')}
                  onClick={() => onPerfilChange(p.key)}
                  aria-pressed={isActive}
                >
                  {isActive && <span className="profile-card-check">{IconCheck}</span>}
                  <span className="profile-card-icon">{PERFIL_ICONS[p.key]}</span>
                  <div className="profile-card-title">{p.title}</div>
                  <div className="profile-card-desc">{p.desc}</div>
                </button>
              )
            })}
          </div>

          <div className="config-time-head">
            <span className="config-time-head-icon">{IconClock}</span>
            <span className="config-time-head-label">Tiempo aproximado</span>
          </div>
          <div className="config-time">
            <div className={'config-time-slider' + (tiempoInsuficiente ? ' config-time-slider--insuf' : '')}>
              <div className="config-time-track-area">
                <div className="config-time-rail" />
                <div className="config-time-fill" style={{ width: `${pctTiempo}%` }} />
                <span
                  className="config-time-min"
                  style={{ left: `${pctMinimo}%` }}
                  title={`Mínimo para modo ${modoTitle}: ${minimoModo} min`}
                >
                  <span className="config-time-min-label">mín</span>
                </span>
                <span className="config-time-bubble" style={{ left: `${pctTiempo}%` }}>
                  {tiempoMaximoMin}<small>min</small>
                </span>
                <div className="config-time-marks">
                  {TIEMPO_MARKS.map(mark => (
                    <span
                      key={mark}
                      className="config-time-mark"
                      style={{ left: `${((mark - TIEMPO_MIN) / (TIEMPO_MAX - TIEMPO_MIN)) * 100}%` }}
                    >
                      {mark}
                    </span>
                  ))}
                </div>
              </div>
              <input
                type="range"
                className="range-input"
                min={TIEMPO_MIN}
                max={TIEMPO_MAX}
                step="1"
                value={tiempoMaximoMin}
                onChange={e => setTiempoMaximo(+e.target.value)}
              />
            </div>
          </div>
          {tiempoInsuficiente ? (
            <div className="config-time-warning">
              <span className="config-time-warning-icon">{IconAlert}</span>
              Por debajo de {minimoModo} min puede no ser aplicable
            </div>
          ) : (
            <div className="config-time-hint">
              <span className="config-time-hint-icon">{IconCheckCircle}</span>
              Aplicable a partir de {minimoModo} min
            </div>
          )}
        </div>
      )}

      {/* ── Paso 3: Ejecución ── */}
      {step === 'ejecucion' && (
        <div className="step-content">
          <div className="exec-summary">
            <div className="exec-summary-item">
              <span className="exec-summary-icon">{IconBox}</span>
              <span className="exec-summary-text">
                <span className="exec-summary-label">OPLs</span>
                <span className="exec-summary-value">{summaryOplCount}</span>
              </span>
            </div>
            <div className="exec-summary-item">
              <span className="exec-summary-icon">{PERFIL_ICONS[summaryPerfilKey]}</span>
              <span className="exec-summary-text">
                <span className="exec-summary-label">Perfil</span>
                <span className="exec-summary-value">{PERFILES.find(p => p.key === summaryPerfilKey)?.title}</span>
              </span>
            </div>
            <div className="exec-summary-item">
              <span className="exec-summary-icon">{IconClock}</span>
              <span className="exec-summary-text">
                <span className="exec-summary-label">Tiempo aproximado</span>
                <span className="exec-summary-value">{summaryTiempo}</span>
              </span>
            </div>
          </div>

          {progreso && (
            <div className="exec-progress">
              <div className="exec-progress-header">
                <div className="exec-progress-header-left">
                  {optimizing && <span className="exec-pulse" />}
                  <span className="exec-progress-title">
                    {optimizing ? 'Optimizando' : 'Progreso'}
                  </span>
                </div>
                {optimizing && (
                  <div className="exec-progress-timer">
                    <span className="exec-progress-timer-digits">{formatoTranscurrido}</span>
                    <span className="exec-progress-timer-label">transcurridos</span>
                  </div>
                )}
              </div>
              <div className="exec-phases">
                {FASES_PROGRESO.map(fase => {
                  const estado = progreso.fases?.[fase.key as keyof typeof progreso.fases] ?? 'PENDIENTE'
                  const upper = estado.toUpperCase()
                  const isRunning = upper === 'EJECUTANDO'
                  const isDone = ['OPTIMA', 'OPTIMAL', 'FACTIBLE', 'FEASIBLE', 'INFACTIBLE', 'INFEASIBLE'].includes(upper)
                  const isSkipped = upper === 'NO_EJECUTADA'
                  const isPending = upper === 'PENDIENTE'

                  return (
                    <div key={fase.key} className={'exec-phase-row' + (isSkipped ? ' exec-phase-row--skipped' : '')}>
                      <div className="exec-phase-info">
                        <div className="exec-phase-name">{fase.label}</div>
                        <div className="exec-phase-desc">{fase.desc}</div>
                      </div>
                      <div className="exec-phase-bar-wrap">
                        <div className={
                          'exec-phase-bar' +
                          (isRunning ? ' exec-phase-bar--running' : '') +
                          (isDone ? ' exec-phase-bar--done' : '') +
                          (isSkipped ? ' exec-phase-bar--skipped' : '')
                        }>
                          {isDone && <div className="exec-phase-bar-fill" />}
                        </div>
                      </div>
                      <div className="exec-phase-status">
                        {isSkipped ? (
                          <span className="exec-phase-off">Off</span>
                        ) : isPending ? (
                          <span className="exec-phase-pending">—</span>
                        ) : isRunning ? (
                          <span className="exec-phase-running-badge">
                            <span className="exec-pulse" />
                            En curso
                          </span>
                        ) : (
                          <span className={estadoBadgeClass(estado)}>
                            {estadoLabel(estado)}
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {optimizeError && (
            <p className="error-msg" style={{ marginTop: '16px' }}>{optimizeError}</p>
          )}
        </div>
      )}

    </div>
  )
}
