import { useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '../../api/client'
import { PAGE_SIZE } from './constantes'
import type { ArticuloOut, OplOut } from '../../api/types'

interface Props {
  articulos: ArticuloOut[]
  onClose: () => void
  onCreated: (opl: OplOut) => void
}

/**
 * Modal para crear una OPL manualmente eligiendo artículo y cantidad.
 * @param articulos Artículos disponibles para asociar a la OPL.
 * @param onClose Cierra el modal sin crear nada.
 * @param onCreated Callback con la OPL creada tras el alta.
 */
export default function AnadirOplManualModal({ articulos, onClose, onCreated }: Props) {
  const [query, setQuery] = useState('')
  const [refSeleccionada, setRefSeleccionada] = useState<string | null>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [cantidad, setCantidad] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const listRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const resultados = useMemo(() => {
    const q = query.trim().toLowerCase()
    const base = !q
      ? articulos
      : articulos.filter(
          a => a.referencia.toLowerCase().includes(q) || a.descripcion.toLowerCase().includes(q),
        )
    return [...base].sort((a, b) =>
      a.referencia.localeCompare(b.referencia, undefined, { numeric: true }),
    )
  }, [articulos, query])

  const visibleRows = resultados.slice(0, visibleCount)

  const articuloSel = useMemo(
    () => articulos.find(a => a.referencia === refSeleccionada) ?? null,
    [articulos, refSeleccionada],
  )

  useEffect(() => {
    setActiveIndex(0)
    setVisibleCount(PAGE_SIZE)
  }, [query])

  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${activeIndex}"]`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0]?.isIntersecting) {
          setVisibleCount(n => Math.min(n + PAGE_SIZE, resultados.length))
        }
      },
      { root: listRef.current, rootMargin: '120px' },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [resultados.length])

  const cant = Number(cantidad)
  const cantValida = Number.isInteger(cant) && cant > 0
  const tiempoEstimado = articuloSel && cantValida
    ? Math.round(cant * articuloSel.tiempo_estandar)
    : null

  function elegir(ref: string) {
    setRefSeleccionada(ref)
    setError('')
  }

  function handleSearchKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (resultados.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex(i => {
        const next = Math.min(i + 1, resultados.length - 1)
        setVisibleCount(n => Math.max(n, next + 1))
        return next
      })
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const a = resultados[activeIndex]
      if (a) elegir(a.referencia)
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!refSeleccionada) { setError('Selecciona un artículo'); return }
    if (!cantValida) { setError('La cantidad debe ser un entero mayor que 0'); return }

    setLoading(true)
    setError('')
    try {
      const opl = await apiFetch<OplOut>('/opls/crear', {
        method: 'POST',
        body: JSON.stringify({ ref_articulo: refSeleccionada, cantidad: cant }),
      })
      onCreated(opl)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear la OPL')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={loading ? undefined : onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Añadir OPL manual</span>
          <button className="modal-close" onClick={onClose} disabled={loading} aria-label="Cerrar">×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '0 0 14px' }}>
              Busca un artículo por referencia o nombre, elígelo e indica la cantidad a montar.
              La OPL se creará con un identificador propio y quedará seleccionada para optimizar.
            </p>

            <div className="opl-search">
              <span className="opl-search-icon" aria-hidden>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M21 21l-4.3-4.3" />
                </svg>
              </span>
              <input
                className="opl-search-input"
                type="search"
                placeholder="Buscar por referencia o nombre de artículo…"
                value={query}
                disabled={loading}
                autoFocus
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleSearchKeyDown}
              />
              {query && (
                <button
                  type="button"
                  className="opl-search-clear"
                  onClick={() => setQuery('')}
                  aria-label="Limpiar búsqueda"
                >
                  ×
                </button>
              )}
            </div>

            <div className="aom-results" ref={listRef}>
              {resultados.length === 0 ? (
                <div className="aom-empty">Sin coincidencias para "{query}"</div>
              ) : (
                <>
                  {visibleRows.map((a, i) => {
                    const cls =
                      'aom-result' +
                      (a.referencia === refSeleccionada ? ' is-selected' : '') +
                      (i === activeIndex ? ' is-active' : '')
                    return (
                      <button
                        type="button"
                        key={a.referencia}
                        data-idx={i}
                        className={cls}
                        disabled={loading}
                        onMouseEnter={() => setActiveIndex(i)}
                        onClick={() => elegir(a.referencia)}
                      >
                        <span className="aom-result-ref">{a.referencia}</span>
                        <span className="aom-result-desc" title={a.descripcion}>{a.descripcion}</span>
                        <span className="aom-result-meta">{Number(a.tiempo_estandar.toFixed(2))} min/ud</span>
                      </button>
                    )
                  })}
                  {visibleCount < resultados.length && (
                    <div ref={sentinelRef} className="aom-loading-more">
                      Mostrando {visibleCount} de {resultados.length}
                    </div>
                  )}
                </>
              )}
            </div>

            {articuloSel && (
              <div className="aom-selected">
                <span className="aom-selected-ref">{articuloSel.referencia}</span>
                <span className="aom-selected-desc" title={articuloSel.descripcion}>{articuloSel.descripcion}</span>
              </div>
            )}

            <div className="aom-qty-block">
              <label className="aom-qty-label" htmlFor="aom-cantidad">Cantidad a montar</label>
              <div className="aom-qty-controls">
                <input
                  id="aom-cantidad"
                  type="number"
                  min={1}
                  step={1}
                  className="aom-qty-input"
                  value={cantidad}
                  disabled={loading}
                  onChange={e => setCantidad(e.target.value)}
                />
                <div className="aom-preview">
                  {tiempoEstimado != null
                    ? <>Tiempo estimado: <strong>{tiempoEstimado} min</strong></>
                    : 'Elige artículo y cantidad para ver el tiempo estimado.'}
                </div>
              </div>
            </div>

            {error && <p className="error-msg" style={{ marginTop: '14px', marginBottom: 0 }}>{error}</p>}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>Cancelar</button>
            <button
              type="submit"
              className="btn-primary"
              style={{ width: 'auto' }}
              disabled={loading || !refSeleccionada || !cantValida}
            >
              {loading ? 'Creando…' : 'Crear OPL'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
