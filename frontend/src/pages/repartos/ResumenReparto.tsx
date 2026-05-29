import { formatSemanaLabel } from '../../utils/semana'
import { FASES_PROGRESO } from './constantes'
import { estadoBadgeClass, estadoLabel } from './utilidades'
import type { RepartoDetalleOut, ResultadoOut, OperarioOut } from '../../api/types'

interface Props {
  semana: string
  isAprobado: boolean
  reparto: RepartoDetalleOut
  operarios: OperarioOut[]
  resultado: ResultadoOut | null
  optimizeError: string
  showFases?: boolean
}

export default function ResumenReparto({
  semana,
  isAprobado,
  reparto,
  operarios,
  resultado,
  optimizeError,
  showFases = true,
}: Props) {
  const asigs = reparto.asignaciones ?? []
  const nAsignadas = asigs.filter(a => a.dni_operario).length
  const nTotal = asigs.length

  const totalAsignadoMin = Math.round(
    asigs.filter(a => a.dni_operario).reduce((sum, a) => sum + (a.tiempo_planificado ?? 0), 0)
  )
  const totalCapacidadMin = operarios.reduce(
    (sum, op) => sum + Math.round(op.horas_semanales * 60),
    0
  )
  const pctUtilizacion = totalCapacidadMin > 0
    ? Math.round((totalAsignadoMin / totalCapacidadMin) * 100)
    : 0
  const pctAsignadas = nTotal > 0 ? Math.round((nAsignadas / nTotal) * 100) : 0

  const nOptimasFromAsigs = nAsignadas > 0
    ? asigs.filter(a => a.dni_operario && a.es_optima === true).length
    : null
  const nOptimas = nOptimasFromAsigs
  const hasBeenOptimized = asigs.some(a => a.dni_operario && a.tipo_asignacion !== 'arrastre')

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">Planificacion semanal</div>
          <div className="card-semana">{formatSemanaLabel(semana)}</div>
        </div>
        <span className={isAprobado ? 'badge badge-ok' : 'badge badge-pending'}>
          {isAprobado ? 'Aprobado' : 'Pendiente'}
        </span>
      </div>

      {nTotal > 0 && hasBeenOptimized && (
        <div style={{
          display: 'flex',
          border: '1px solid var(--border)',
          borderRadius: 8,
          overflow: 'hidden',
          marginTop: 16,
        }}>
          {/* Celda 1: ratio asignadas */}
          <div style={{
            flex: 1,
            padding: '14px 16px',
            background: 'var(--bg)',
            borderRight: '1px solid var(--border)',
          }}>
            <div style={{
              fontSize: 26,
              fontWeight: 700,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.02em',
              lineHeight: 1,
              color: 'var(--text)',
            }}>
              {nAsignadas}<span style={{ fontSize: 16, fontWeight: 400, color: 'var(--text-muted)' }}> / {nTotal}</span>
            </div>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginTop: 5 }}>
              OPLs asignadas
            </div>
            <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, marginTop: 8, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${pctAsignadas}%`, background: '#2563eb', borderRadius: 2, transition: 'width 0.4s ease' }} />
            </div>
          </div>

          {/* Celda 2: utilización operarios */}
          <div style={{
            flex: 1,
            padding: '14px 16px',
            background: 'var(--bg)',
            borderRight: '1px solid var(--border)',
          }}>
            <div style={{
              fontSize: 26,
              fontWeight: 700,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.02em',
              lineHeight: 1,
              color: 'var(--text)',
            }}>
              {pctUtilizacion}<span style={{ fontSize: 16, fontWeight: 400, color: 'var(--text-muted)' }}>%</span>
            </div>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginTop: 5 }}>
              Uso operarios
            </div>
          </div>

          {/* Celda 3: óptimas solver */}
          <div style={{
            flex: 1,
            padding: '14px 16px',
            background: 'var(--bg)',
          }}>
            <div style={{
              fontSize: 26,
              fontWeight: 700,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.02em',
              lineHeight: 1,
              color: 'var(--text)',
            }}>
              {nOptimas ?? '—'}
            </div>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginTop: 5 }}>
              Óptimas
            </div>
          </div>
        </div>
      )}

      {showFases && reparto.estado_base != null && (
        <div className="exec-phases" style={{ marginTop: 16 }}>
          {FASES_PROGRESO.map(fase => {
            const estadoKey = `estado_${fase.key}` as keyof RepartoDetalleOut
            const estadoVal = (resultado?.[estadoKey as keyof ResultadoOut] ?? reparto[estadoKey]) as string | null | undefined
            if (!estadoVal) return null

            const upper = estadoVal.toUpperCase()
            const isSkipped = upper === 'NO_EJECUTADA'
            const isDone = ['OPTIMA', 'OPTIMAL', 'FACTIBLE', 'FEASIBLE', 'INFACTIBLE', 'INFEASIBLE'].includes(upper)

            return (
              <div key={fase.key} className={'exec-phase-row' + (isSkipped ? ' exec-phase-row--skipped' : '')}>
                <div className="exec-phase-info">
                  <div className="exec-phase-name">{fase.label}</div>
                  <div className="exec-phase-desc">{fase.desc}</div>
                </div>
                <div className="exec-phase-bar-wrap">
                  <div
                    className={
                      'exec-phase-bar' +
                      (isDone ? ' exec-phase-bar--done' : '') +
                      (isSkipped ? ' exec-phase-bar--skipped' : '')
                    }
                  >
                    {isDone && <div className="exec-phase-bar-fill" />}
                  </div>
                </div>
                <div className="exec-phase-status">
                  {isSkipped ? (
                    <span className="exec-phase-off">Off</span>
                  ) : (
                    <span className={estadoBadgeClass(estadoVal)}>{estadoLabel(estadoVal)}</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {isAprobado && (
        <div className="reparto-locked-banner">
          Reparto aprobado - solo lectura.
        </div>
      )}

      {optimizeError && (
        <p className="error-msg" style={{ marginTop: 16 }}>{optimizeError}</p>
      )}
    </div>
  )
}
