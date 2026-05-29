import { useEffect, useRef, useState, type ReactNode } from 'react'
import { apiFetch, apiUpload, apiFetchBlob } from '../api/client'
import type { CargaOut } from '../api/types'
import { useSolver } from '../context/useSolver'

// ── Iconos ──────────────────────────────────────────────────────────────────

function Icon({ paths, size = 16 }: { paths: ReactNode; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths}
    </svg>
  )
}
const IconLayers     = <Icon paths={<><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></>} />
const IconBox        = <Icon paths={<><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><path d="M3.3 7L12 12l8.7-5M12 22V12" /></>} />
const IconUsers      = <Icon paths={<><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>} />
const IconStar       = <Icon paths={<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />} />
const IconClock      = <Icon paths={<><circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15 14" /></>} />
const IconClipboard  = <Icon paths={<><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /><line x1="8" y1="12" x2="16" y2="12" /><line x1="8" y1="16" x2="13" y2="16" /></>} />
const IconDownload   = <Icon paths={<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></>} />
const IconUpload     = <Icon paths={<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></>} />

// ── Tipos locales ─────────────────────────────────────────────────────────────

interface ColDef {
  key: string
  label: string
  numeric?: boolean   // alineación a la derecha + cifras tabulares
  decimals?: boolean  // fuerza siempre 2 decimales
  mono?: boolean
}

interface TabDef {
  key: string
  label: string
  endpoint: string
  icon: ReactNode
  cols: ColDef[]
}

interface EntidadImport {
  key: string
  label: string
}

// ── Configuración estática ────────────────────────────────────────────────────

const TABS: TabDef[] = [
  {
    key: 'familias',
    label: 'Familias',
    endpoint: '/familias',
    icon: IconLayers,
    cols: [
      { key: 'descripcion',          label: 'Descripción' },
      { key: 'experiencia_requerida', label: 'Exp. requerida', numeric: true },
    ],
  },
  {
    key: 'articulos',
    label: 'Artículos',
    endpoint: '/articulos',
    icon: IconBox,
    cols: [
      { key: 'referencia',    label: 'Referencia', mono: true },
      { key: 'familia',       label: 'Familia' },
      { key: 'descripcion',   label: 'Descripción' },
      { key: 'peso',          label: 'Peso (kg)', numeric: true, decimals: true },
      { key: 'tiempo_estandar', label: 'T. estándar (min)', numeric: true, decimals: true },
    ],
  },
  {
    key: 'operarios',
    label: 'Operarios',
    endpoint: '/operarios',
    icon: IconUsers,
    cols: [
      { key: 'dni',              label: 'DNI', mono: true },
      { key: 'nombre_completo',  label: 'Nombre' },
      { key: 'horas_semanales',  label: 'Horas/semana', numeric: true },
    ],
  },
  {
    key: 'operario-familia',
    label: 'Skills',
    endpoint: '/operario-familia',
    icon: IconStar,
    cols: [
      { key: 'dni_operario', label: 'DNI operario', mono: true },
      { key: 'familia',      label: 'Familia' },
      { key: 'experiencia',  label: 'Experiencia', numeric: true },
    ],
  },
  {
    key: 'operario-articulo',
    label: 'Tiempos',
    endpoint: '/operario-articulo',
    icon: IconClock,
    cols: [
      { key: 'ref_articulo',    label: 'Artículo', mono: true },
      { key: 'dni_operario',    label: 'DNI operario', mono: true },
      { key: 'tiempo_estimado', label: 'T. estimado (min)', numeric: true, decimals: true },
    ],
  },
  {
    key: 'opls',
    label: 'OPLs',
    endpoint: '/opls',
    icon: IconClipboard,
    cols: [
      { key: 'id',              label: 'ID', mono: true },
      { key: 'ref_articulo',    label: 'Artículo', mono: true },
      { key: 'cantidad',        label: 'Cantidad', numeric: true },
      { key: 'tiempo_estimado', label: 'T. estimado (min)', numeric: true, decimals: true },
      { key: 'asignado_a',      label: 'Asignado a' },
    ],
  },
]

const ENTIDADES_IMPORT: EntidadImport[] = [
  { key: 'familias',          label: 'Familias' },
  { key: 'articulos',         label: 'Artículos' },
  { key: 'operarios',         label: 'Operarios' },
  { key: 'operario_familia',  label: 'Skills (Op-Familia)' },
  { key: 'operario_articulo', label: 'Tiempos (Op-Artículo)' },
  { key: 'opls',              label: 'OPLs' },
]

// ── Sub-componentes ────────────────────────────────────────────────────────────

const PAGE_SIZE = 50

function fmtCell(value: unknown, decimals?: boolean): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') {
    if (decimals) return value.toFixed(2)
    return Number.isInteger(value) ? String(value) : value.toFixed(2)
  }
  return String(value)
}

function DataTable({ cols, rows, loading, error }: {
  cols: ColDef[]
  rows: Record<string, unknown>[] | null
  loading: boolean
  error: string
}) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const sentinelRef = useRef<HTMLDivElement>(null)

  useEffect(() => { setVisibleCount(PAGE_SIZE) }, [rows])

  useEffect(() => {
    if (!sentinelRef.current) return
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0]!.isIntersecting) {
          setVisibleCount(n => Math.min(n + PAGE_SIZE, rows?.length ?? 0))
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [rows])

  if (loading) return <p style={{ color: 'var(--text-muted)', padding: '16px 0' }}>Cargando...</p>
  if (error)   return <p className="error-msg">{error}</p>
  if (!rows || rows.length === 0) return (
    <div className="table-empty">Sin datos</div>
  )

  const visibleRows = rows.slice(0, visibleCount)

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {cols.map(c => <th key={c.key} className={c.numeric ? 'cell-num' : undefined}>{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, i) => (
            <tr key={i}>
              {cols.map(c => {
                const cls = [c.numeric && 'cell-num', c.mono && 'cell-mono'].filter(Boolean).join(' ')
                return (
                  <td key={c.key} className={cls || undefined}>{fmtCell(row[c.key], c.decimals)}</td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {visibleCount < rows.length && (
        <div ref={sentinelRef} style={{ padding: '12px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Mostrando {visibleCount} de {rows.length}
        </div>
      )}
    </div>
  )
}

function ImportModal({ onClose, onImportDone }: { onClose: () => void; onImportDone: () => void }) {
  const [entidades, setEntidades] = useState<string[]>(() => ENTIDADES_IMPORT.map(e => e.key))
  const [modo, setModo]           = useState('actualizar')
  const [archivo, setArchivo]     = useState<File | null>(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [resultado, setResultado] = useState<CargaOut | null>(null)

  const hasErrors = resultado && Object.values(resultado).some(r => r && r.omitidos > 0)

  function toggleEntidad(key: string) {
    setEntidades(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    )
  }

  function toggleAll() {
    setEntidades(prev =>
      prev.length === ENTIDADES_IMPORT.length ? [] : ENTIDADES_IMPORT.map(e => e.key)
    )
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!archivo) { setError('Selecciona un archivo Excel'); return }
    if (entidades.length === 0) { setError('Selecciona al menos una entidad'); return }

    setLoading(true)
    setError('')
    setResultado(null)

    try {
      const params = new URLSearchParams({ modo })
      entidades.forEach(ent => params.append('entidades', ent))

      const formData = new FormData()
      formData.append('archivo', archivo)

      const data = await apiUpload<CargaOut>(`/carga?${params}`, formData)
      setResultado(data)
      onImportDone()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al importar')
    } finally {
      setLoading(false)
    }
  }

  async function handleDescargarErrores() {
    try {
      await apiFetchBlob('/carga/errores/excel', 'errores_importacion.xlsx')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error')
    }
  }

  return (
    <div className="modal-overlay" onClick={loading ? undefined : onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Importar desde Excel</span>
          <button className="modal-close" onClick={onClose} disabled={loading} aria-label="Cerrar">×</button>
        </div>

        {!resultado ? (
          <form onSubmit={handleSubmit}>
            <fieldset disabled={loading} style={{ border: 'none', padding: 0, margin: 0 }}>
            <div className="modal-body">
              <div className="modal-section-label">Entidades a importar</div>
              <label className="check-all-label">
                <input
                  type="checkbox"
                  checked={entidades.length === ENTIDADES_IMPORT.length}
                  onChange={toggleAll}
                />
                Todas
              </label>
              <div className="entity-check-grid">
                {ENTIDADES_IMPORT.map(e => (
                  <label key={e.key} className="entity-check-item">
                    <input
                      type="checkbox"
                      checked={entidades.includes(e.key)}
                      onChange={() => toggleEntidad(e.key)}
                    />
                    {e.label}
                  </label>
                ))}
              </div>

              <div className="modal-section-label" style={{ marginTop: '16px' }}>Modo de carga</div>
              <div className="radio-group">
                {[
                  { value: 'actualizar',  label: 'Actualizar — añade o modifica sin borrar' },
                  { value: 'reemplazar',  label: 'Reemplazar — borra y recarga las entidades seleccionadas' },
                ].map(opt => (
                  <label key={opt.value} className="radio-item">
                    <input
                      type="radio"
                      name="modo"
                      value={opt.value}
                      checked={modo === opt.value}
                      onChange={() => setModo(opt.value)}
                    />
                    {opt.label}
                  </label>
                ))}
              </div>

              <div className="modal-section-label" style={{ marginTop: '16px' }}>Archivo Excel</div>
              <input
                type="file"
                accept=".xlsx,.xls"
                className="file-input"
                onChange={e => setArchivo(e.target.files?.[0] ?? null)}
              />

              {error && <p className="error-msg" style={{ marginTop: '12px' }}>{error}</p>}
            </div>
            </fieldset>

            <div className="modal-footer">
              <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>Cancelar</button>
              <button type="submit" className="btn-primary" style={{ width: 'auto' }} disabled={loading}>
                {loading ? 'Importando...' : 'Importar'}
              </button>
            </div>
          </form>
        ) : (
          <div>
            <div className="modal-body">
              <div className="import-result-grid">
                {ENTIDADES_IMPORT.map(e => {
                  const r = resultado[e.key as keyof CargaOut]
                  if (!r) return null
                  return (
                    <div key={e.key} className="import-result-row">
                      <span className="import-result-name">{e.label}</span>
                      <span className="import-result-ok">{r.importados} importados</span>
                      {r.omitidos > 0 && (
                        <span className="import-result-warn">{r.omitidos} omitidos</span>
                      )}
                    </div>
                  )
                })}
              </div>
              {error && <p className="error-msg" style={{ marginTop: '12px' }}>{error}</p>}
            </div>
            <div className="modal-footer">
              {hasErrors && (
                <button className="btn-danger-outline" onClick={handleDescargarErrores}>
                  Descargar errores
                </button>
              )}
              <button className="btn-primary" style={{ width: 'auto' }} onClick={onClose}>
                Cerrar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ExportModal({ onClose }: { onClose: () => void }) {
  const [entidades, setEntidades] = useState<string[]>(() => ENTIDADES_IMPORT.map(e => e.key))
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')

  function toggleEntidad(key: string) {
    setEntidades(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    )
  }

  function toggleAll() {
    setEntidades(prev =>
      prev.length === ENTIDADES_IMPORT.length ? [] : ENTIDADES_IMPORT.map(e => e.key)
    )
  }

  async function handleExport() {
    if (entidades.length === 0) { setError('Selecciona al menos una entidad'); return }
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      entidades.forEach(ent => params.append('entidades', ent))
      await apiFetchBlob(`/exportar/excel?${params}`, 'datos.xlsx')
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error')
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={loading ? undefined : onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Exportar a Excel</span>
          <button className="modal-close" onClick={onClose} disabled={loading} aria-label="Cerrar">×</button>
        </div>

        <fieldset disabled={loading} style={{ border: 'none', padding: 0, margin: 0 }}>
        <div className="modal-body">
          <div className="modal-section-label">Entidades a exportar</div>
          <label className="check-all-label">
            <input
              type="checkbox"
              checked={entidades.length === ENTIDADES_IMPORT.length}
              onChange={toggleAll}
            />
            Todas
          </label>
          <div className="entity-check-grid">
            {ENTIDADES_IMPORT.map(e => (
              <label key={e.key} className="entity-check-item">
                <input
                  type="checkbox"
                  checked={entidades.includes(e.key)}
                  onChange={() => toggleEntidad(e.key)}
                />
                {e.label}
              </label>
            ))}
          </div>
          {error && <p className="error-msg" style={{ marginTop: '12px' }}>{error}</p>}
        </div>
        </fieldset>

        <div className="modal-footer">
          <button className="btn-ghost" onClick={onClose} disabled={loading}>Cancelar</button>
          <button className="btn-primary" style={{ width: 'auto' }} onClick={handleExport} disabled={loading}>
            {loading ? 'Exportando...' : 'Exportar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Página principal ───────────────────────────────────────────────────────────

export default function DatosMaestros() {
  const [activeTab, setActiveTab]   = useState(TABS[0]!.key)
  const [rows, setRows]             = useState<Record<string, unknown>[] | null>(null)
  const [loadError, setLoadError]   = useState('')
  const [showImport, setShowImport] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const { activo: solverActivo } = useSolver()

  const tab = TABS.find(t => t.key === activeTab)!

  useEffect(() => {
    setRows(null)
    setLoadError('')
    apiFetch<Record<string, unknown>[]>(tab.endpoint)
      .then(data => setRows(data))
      .catch(err => setLoadError(err instanceof Error ? err.message : 'Error'))
  }, [activeTab, tab.endpoint])

  function handleImportDone() {
    setRows(null)
    setLoadError('')
    apiFetch<Record<string, unknown>[]>(tab.endpoint)
      .then(data => setRows(data))
      .catch(err => setLoadError(err instanceof Error ? err.message : 'Error'))
  }

  return (
    <>
      <div className="page-header-row">
        <h1 className="page-title" style={{ marginBottom: 0 }}>Datos maestros</h1>
        <div className="page-actions">
          <button className="btn-secondary dm-btn-icon" onClick={() => setShowExport(true)}>
            {IconUpload}<span>Exportar</span>
          </button>
          <button
            className="btn-primary dm-btn-icon"
            style={{ width: 'auto' }}
            onClick={() => setShowImport(true)}
            disabled={solverActivo}
            title={solverActivo ? 'Bloqueado: optimización en curso' : undefined}
          >{IconDownload}<span>Importar</span></button>
        </div>
      </div>

      <div className="tabs-bar">
        {TABS.map(t => (
          <button
            key={t.key}
            className={'tab-btn dm-tab' + (t.key === activeTab ? ' active' : '')}
            onClick={() => setActiveTab(t.key)}
          >
            <span className="dm-tab-icon">{t.icon}</span>
            {t.label}
            {t.key === activeTab && rows !== null && (
              <span className="dm-tab-count">{rows.length}</span>
            )}
          </button>
        ))}
      </div>

      <div style={{ marginTop: '16px' }}>
        <DataTable
          cols={tab.cols}
          rows={rows}
          loading={rows === null && !loadError}
          error={loadError}
        />
      </div>

      {showImport && (
        <ImportModal
          onClose={() => setShowImport(false)}
          onImportDone={handleImportDone}
        />
      )}
      {showExport && (
        <ExportModal onClose={() => setShowExport(false)} />
      )}
    </>
  )
}
