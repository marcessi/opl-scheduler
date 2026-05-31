import { useMemo, useState, type ReactNode } from 'react'

export type PegarResult = {
  seleccionadas: string[]
  yaRepartidas: string[]
  noExisten: string[]
}

interface Props {
  onClose: () => void
  onPegarDone: (ids: string[]) => PegarResult
}

/* ── Iconos (lucide-style) ─────────────────────────────────────── */
function Icon({ paths, size = 18 }: { paths: ReactNode; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths}
    </svg>
  )
}
const IconCheck = <Icon paths={<polyline points="20 6 9 17 4 12" />} />
const IconLock = <Icon paths={<><rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></>} />
const IconBan = <Icon paths={<><circle cx="12" cy="12" r="9" /><line x1="6" y1="6" x2="18" y2="18" /></>} />
const IconClipboard = <Icon size={16} paths={<><rect x="8" y="2" width="8" height="4" rx="1" /><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /></>} />

/**
 * Separa una columna pegada (de Excel) en IDs únicos, preservando el orden.
 * Solo divide por saltos de línea: los IDs pueden contener espacios (p.ej. "OPL CS210").
 */
function parsearIds(texto: string): string[] {
  const vistos = new Set<string>()
  const ids: string[] = []
  for (const linea of texto.split(/\r?\n/)) {
    const id = linea.trim()
    if (!id || vistos.has(id)) continue
    vistos.add(id)
    ids.push(id)
  }
  return ids
}

function ResultCard({ variant, icon, count, label }: {
  variant: 'ok' | 'warn' | 'bad'
  icon: ReactNode
  count: number
  label: string
}) {
  return (
    <div className={`paste-result-card paste-result-card--${variant}`}>
      <span className="paste-result-icon">{icon}</span>
      <div className="paste-result-text">
        <span className="paste-result-num">{count}</span>
        <span className="paste-result-label">{label}</span>
      </div>
    </div>
  )
}

/**
 * Modal para pegar OPLs en bloque desde el portapapeles (p. ej. copiadas de Excel).
 * @param onClose Cierra el modal.
 * @param onPegarDone Callback al terminar el pegado/importación.
 */
export default function PegarOplModal({ onClose, onPegarDone }: Props) {
  const [texto, setTexto] = useState('')
  const [resultado, setResultado] = useState<PegarResult | null>(null)

  const idsDetectados = useMemo(() => parsearIds(texto), [texto])

  function handleSeleccionar() {
    if (idsDetectados.length === 0) return
    setResultado(onPegarDone(idsDetectados))
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Pegar OPLs</span>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">×</button>
        </div>

        {!resultado ? (
          <>
            <div className="modal-body">
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '0 0 14px', lineHeight: 1.5 }}>
                Copia la columna de <strong>IDs de OPL</strong> desde Excel y pégala aquí. Se
                seleccionarán automáticamente todas las que estén disponibles esta semana.
              </p>
              <div className="paste-field">
                <textarea
                  className="paste-textarea"
                  autoFocus
                  value={texto}
                  onChange={e => setTexto(e.target.value)}
                  placeholder={'OPL163002\nOPL159040\nOPL CS210\n…'}
                  spellCheck={false}
                />
                <span className={'paste-badge' + (idsDetectados.length > 0 ? ' is-active' : '')}>
                  {IconClipboard}
                  {idsDetectados.length > 0
                    ? <><strong>{idsDetectados.length}</strong>&nbsp;detectada{idsDetectados.length !== 1 ? 's' : ''}</>
                    : 'Vacío'}
                </span>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
              <button
                type="button"
                className="btn-primary"
                style={{ width: 'auto' }}
                onClick={handleSeleccionar}
                disabled={idsDetectados.length === 0}
              >
                Seleccionar
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="modal-body">
              <div className="paste-result">
                <ResultCard
                  variant="ok"
                  icon={IconCheck}
                  count={resultado.seleccionadas.length}
                  label="Seleccionadas"
                />
                {resultado.yaRepartidas.length > 0 && (
                  <ResultCard
                    variant="warn"
                    icon={IconLock}
                    count={resultado.yaRepartidas.length}
                    label="Ya repartidas"
                  />
                )}
                {resultado.noExisten.length > 0 && (
                  <ResultCard
                    variant="bad"
                    icon={IconBan}
                    count={resultado.noExisten.length}
                    label="No existen"
                  />
                )}
              </div>

              {resultado.noExisten.length > 0 && (
                <div className="paste-notfound">
                  <div className="paste-notfound-label">IDs no encontrados</div>
                  <div className="paste-notfound-list">
                    {resultado.noExisten.join(', ')}
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-ghost"
                onClick={() => { setTexto(''); setResultado(null) }}
              >
                Pegar más
              </button>
              <button type="button" className="btn-primary" style={{ width: 'auto' }} onClick={onClose}>
                Cerrar
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
