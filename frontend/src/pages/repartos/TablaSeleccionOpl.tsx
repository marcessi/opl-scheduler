import { useEffect, useMemo, useRef, useState } from 'react'
import { PAGE_SIZE } from './constantes'
import type { OplOut } from '../../api/types'

interface Props {
  opls: OplOut[] | null
  selectedIds: string[]
  obligatoriaIds?: string[]
  onChange: (ids: string[]) => void
  articulosByRef?: Map<string, string>
  searchable?: boolean
}

/**
 * Tabla de selección de OPLs con búsqueda, scroll infinito y selección por rango.
 * @param opls OPLs a listar (`null` mientras cargan).
 * @param selectedIds Ids actualmente seleccionados.
 * @param obligatoriaIds Ids marcados como obligatorios (no deseleccionables).
 * @param onChange Callback con la nueva selección de ids.
 * @param articulosByRef Mapa referencia→nombre de artículo para mostrar descripciones.
 * @param searchable Si se muestra el buscador.
 */
export default function TablaSeleccionOpl({
  opls,
  selectedIds,
  obligatoriaIds = [],
  onChange,
  articulosByRef,
  searchable = true,
}: Props) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [query, setQuery] = useState('')
  const [anchorId, setAnchorId] = useState<string | null>(null)
  const [showSelectedOnly, setShowSelectedOnly] = useState(false)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const obligatoriaSet = useMemo(() => new Set(obligatoriaIds), [obligatoriaIds])
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])

  const sorted = useMemo(() => {
    if (!opls) return null
    return [...opls].sort((a, b) => {
      const aObl = obligatoriaSet.has(a.id) ? 0 : 1
      const bObl = obligatoriaSet.has(b.id) ? 0 : 1
      if (aObl !== bObl) return aObl - bObl
      return a.id.localeCompare(b.id, undefined, { numeric: true })
    })
  }, [opls, obligatoriaSet])

  const filtered = useMemo(() => {
    if (!sorted) return null
    const q = query.trim().toLowerCase()
    return sorted.filter(o => {
      if (showSelectedOnly && !selectedSet.has(o.id) && !obligatoriaSet.has(o.id)) return false
      if (!q) return true
      if (o.id.toLowerCase().includes(q)) return true
      if (o.ref_articulo.toLowerCase().includes(q)) return true
      const nombre = articulosByRef?.get(o.ref_articulo) ?? ''
      return nombre.toLowerCase().includes(q)
    })
  }, [sorted, query, articulosByRef, showSelectedOnly, selectedSet, obligatoriaSet])

  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [opls?.length, query])

  useEffect(() => {
    if (!sentinelRef.current) return
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0]!.isIntersecting) {
          setVisibleCount(n => Math.min(n + PAGE_SIZE, filtered?.length ?? 0))
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [filtered?.length])

  if (!sorted || sorted.length === 0) {
    return <div className="table-empty">No hay OPLs disponibles</div>
  }

  const idsFiltradosNormales = (filtered ?? [])
    .filter(o => !obligatoriaSet.has(o.id))
    .map(o => o.id)
  const visibleNormalesCount = idsFiltradosNormales.length
  const allFilteredSelected =
    visibleNormalesCount > 0 &&
    idsFiltradosNormales.every(id => selectedSet.has(id))
  const someFilteredSelected =
    !allFilteredSelected &&
    idsFiltradosNormales.some(id => selectedSet.has(id))

  const visibleRows = (filtered ?? []).slice(0, visibleCount)

  function commit(next: Set<string>) {
    onChange([...next])
  }

  function toggleAllFiltered() {
    const next = new Set(selectedSet)
    if (allFilteredSelected) {
      idsFiltradosNormales.forEach(id => next.delete(id))
    } else {
      idsFiltradosNormales.forEach(id => next.add(id))
    }
    commit(next)
  }

  function handleRowClick(e: React.MouseEvent, opl: OplOut, index: number) {
    if (obligatoriaSet.has(opl.id)) return
    const willSelect = !selectedSet.has(opl.id)
    const next = new Set(selectedSet)

    if (e.shiftKey && anchorId) {
      const anchorIdx = visibleRows.findIndex(r => r.id === anchorId)
      if (anchorIdx >= 0 && anchorIdx !== index) {
        const [start, end] = anchorIdx < index ? [anchorIdx, index] : [index, anchorIdx]
        for (let i = start; i <= end; i++) {
          const r = visibleRows[i]
          if (r && !obligatoriaSet.has(r.id)) {
            if (willSelect) next.add(r.id)
            else next.delete(r.id)
          }
        }
        commit(next)
        setAnchorId(opl.id)
        return
      }
    }

    if (willSelect) next.add(opl.id)
    else next.delete(opl.id)
    commit(next)
    setAnchorId(opl.id)
  }

  function grupo(opl: OplOut): number {
    return obligatoriaSet.has(opl.id) ? 0 : 1
  }

  return (
    <div className="opl-table-container">
      {searchable && (
        <div className="opl-toolbar">
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
              placeholder="Buscar por OPL, referencia o nombre de artículo…"
              value={query}
              onChange={e => setQuery(e.target.value)}
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
          <button
            type="button"
            className={'btn-ghost opl-filter-toggle' + (showSelectedOnly ? ' is-active' : '')}
            onClick={() => setShowSelectedOnly(v => !v)}
            aria-pressed={showSelectedOnly}
          >
            Solo seleccionadas
          </button>
          <span className="opl-shift-hint">Mantén <kbd>Shift</kbd> al hacer click para seleccionar un rango</span>
        </div>
      )}

      <div className="table-wrap">
        <table className="opl-table">
          <thead>
            <tr>
              <th className="table-check-col">
                <input
                  type="checkbox"
                  checked={allFilteredSelected}
                  ref={el => {
                    if (el) el.indeterminate = someFilteredSelected
                  }}
                  onChange={toggleAllFiltered}
                  aria-label="Seleccionar todos los visibles"
                />
              </th>
              <th>OPL</th>
              <th>Ref.</th>
              <th>Artículo</th>
              <th style={{ textAlign: 'right' }}>Cantidad</th>
              <th style={{ textAlign: 'right' }}>T. est. (min)</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.length === 0 ? (
              <tr>
                <td colSpan={6} className="table-empty" style={{ padding: 32 }}>
                  Sin coincidencias para "{query}"
                </td>
              </tr>
            ) : (
              visibleRows.map((opl, i) => {
                const isObligatoria = obligatoriaSet.has(opl.id)
                const checked = selectedSet.has(opl.id)
                const showDivider = i > 0 && grupo(opl) !== grupo(visibleRows[i - 1]!)
                const nombre = articulosByRef?.get(opl.ref_articulo) ?? '—'
                const rowClass =
                  'opl-row' +
                  (isObligatoria ? ' opl-row--obligatoria' : '') +
                  (!isObligatoria && checked ? ' opl-row--selected' : '') +
                  (showDivider ? ' opl-divider-row' : '')
                return (
                  <tr
                    key={opl.id}
                    className={rowClass}
                    style={isObligatoria ? undefined : { userSelect: 'none', cursor: 'pointer' }}
                    onMouseDown={isObligatoria ? undefined : e => { if (e.shiftKey) e.preventDefault() }}
                    onClick={isObligatoria ? undefined : e => handleRowClick(e, opl, i)}
                  >
                    <td className="table-check-col">
                      <input
                        type="checkbox"
                        checked={isObligatoria || checked}
                        disabled={isObligatoria}
                        readOnly
                        tabIndex={-1}
                        style={{ pointerEvents: 'none' }}
                      />
                    </td>
                    <td
                      title={opl.id}
                      style={{
                        maxWidth: 180,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {isObligatoria && <span className="badge-obligatoria">Oblig.</span>}
                      {opl.id}
                    </td>
                    <td
                      title={opl.ref_articulo}
                      style={{
                        maxWidth: 140,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      {opl.ref_articulo}
                    </td>
                    <td
                      title={nombre}
                      style={{
                        maxWidth: 320,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {nombre}
                    </td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                      {opl.cantidad}
                    </td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                      {opl.tiempo_estimado}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
        {visibleCount < (filtered?.length ?? 0) && (
          <div
            ref={sentinelRef}
            style={{
              padding: '12px 0',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.85rem',
            }}
          >
            Mostrando {visibleCount} de {filtered?.length}
          </div>
        )}
      </div>
    </div>
  )
}
