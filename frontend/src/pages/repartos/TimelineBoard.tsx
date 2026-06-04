import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import type { AsignacionDetalleOut, OplOut, OperarioOut } from '../../api/types'
import TablaSeleccionOpl from './TablaSeleccionOpl'

// ── Constants ─────────────────────────────────────────────────────────────────

const MIN_OPL_VISIBLE_PX = 6     // px que ocupará la OPL más corta del reparto
const LABEL_COL_PX       = 160
const ZOOM_MIN  = 0.5
const ZOOM_MAX  = 4
const ZOOM_STEP = 1.33
const ZOOM_KEY  = 'timelineBoard.zoom'

// ── Helpers ───────────────────────────────────────────────────────────────────

function colorBloque(tipo: string): string {
  if (tipo === 'arrastre')    return '#5b21b6'
  if (tipo === 'obligatoria') return '#dc2626'
  return '#2563eb'
}

function esParcialOpl(o: AsignacionDetalleOut): boolean {
  return (o.tiempo_total_teorico ?? o.tiempo_planificado ?? 0) - (o.tiempo_planificado ?? 0) > 0.5
}

function prefixOpl(opl: AsignacionDetalleOut): string {
  if (opl.tipo_asignacion === 'arrastre') return '⚓ '
  return ''
}

function matchesQuery(opl: AsignacionDetalleOut, q: string): boolean {
  if (!q) return true
  const needle = q.toLowerCase()
  return (
    opl.id_opl.toLowerCase().includes(needle) ||
    (opl.ref_articulo ?? '').toLowerCase().includes(needle) ||
    (opl.nombre_articulo ?? '').toLowerCase().includes(needle) ||
    (opl.ref_familia ?? '').toLowerCase().includes(needle)
  )
}

function highlight(text: string, needle: string): ReactNode {
  if (!needle) return text
  const lower = text.toLowerCase()
  const idx = lower.indexOf(needle.toLowerCase())
  if (idx === -1) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ background: 'rgba(250, 204, 21, 0.55)', color: 'inherit', padding: '0 1px', borderRadius: 2, fontWeight: 700 }}>
        {text.slice(idx, idx + needle.length)}
      </mark>
      {text.slice(idx + needle.length)}
    </>
  )
}

// ── Iconos SVG inline ─────────────────────────────────────────────────────────

const IconSearch = ({ size = 14, color = 'currentColor' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </svg>
)

const IconX = ({ size = 12, color = 'currentColor' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M18 6 6 18" /><path d="m6 6 12 12" />
  </svg>
)

const IconOpl = ({ size = 12, color = 'currentColor' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M7 9h10M7 13h6" />
  </svg>
)

const IconArticulo = ({ size = 12, color = 'currentColor' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="m7.5 4.27 9 5.15" />
    <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
    <path d="m3.3 7 8.7 5 8.7-5" />
    <path d="M12 22V12" />
  </svg>
)

const IconFamilia = ({ size = 12, color = 'currentColor' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
  </svg>
)

const IconArrow = ({ size = 10, color = 'currentColor' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
  </svg>
)

// ── Tipos de sugerencia para lista plana (nav por teclado) ────────────────────

type Suggestion =
  | { kind: 'opl'; value: string }
  | { kind: 'articulo'; value: string; nombre: string }
  | { kind: 'familia'; value: string }

// ── Sub-componentes del dropdown ──────────────────────────────────────────────

function SectionHeader({ icon, label, count, accent, collapsed, onToggle }: {
  icon: ReactNode
  label: string
  count: number
  accent: string
  collapsed: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onMouseDown={e => { e.preventDefault(); onToggle() }}
      aria-expanded={!collapsed}
      style={{
        width: '100%', background: 'transparent', border: 'none',
        padding: '9px 14px 5px', cursor: 'pointer',
        fontSize: 10, fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: '0.08em',
        color: '#6b7280',
        display: 'flex', alignItems: 'center', gap: 7,
        textAlign: 'left',
      }}
    >
      <span
        aria-hidden
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: 12, height: 12, color: '#9ca3af',
          transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
          transition: 'transform 140ms cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </span>
      <span style={{ color: accent, display: 'inline-flex' }}>{icon}</span>
      <span>{label}</span>
      <span style={{
        marginLeft: 'auto',
        fontSize: 10, fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        padding: '1px 6px',
        background: 'rgba(107,114,128,0.12)',
        color: '#374151',
        borderRadius: 999,
        letterSpacing: 0,
      }}>{count}</span>
    </button>
  )
}


interface Packed {
  opl: AsignacionDetalleOut
  leftPx: number
  widthPx: number
}

// Reparte ancho con suelo MIN_OPL_VISIBLE_PX. Filas llenas/sobrecarga terminan exactamente en max(capPx, realPx).
// Filas no llenas: lineal con min-width (deja hueco al final).
function packPx(opls: AsignacionDetalleOut[], pxPerMin: number, capPx: number): Packed[] {
  const items = opls.map(o => ({
    opl: o,
    min: o.tiempo_planificado ?? 0,
    px: 0,
    fixed: false,
  }))
  const totalMin = items.reduce((s, i) => s + i.min, 0)
  if (totalMin === 0) return []

  const realPx  = totalMin * pxPerMin
  const capMin  = pxPerMin > 0 ? capPx / pxPerMin : 0
  const lleno   = totalMin >= capMin - 0.01

  if (!lleno) {
    let cursor = 0
    return items.map(({ opl, min }) => {
      const leftPx  = Math.round(cursor)
      cursor += Math.max(MIN_OPL_VISIBLE_PX, min * pxPerMin)
      const widthPx = Math.round(cursor) - leftPx
      return { opl, leftPx, widthPx }
    })
  }

  const target = Math.max(capPx, realPx)
  let remainingPx  = target
  let remainingMin = totalMin
  let changed = true
  while (changed && remainingMin > 0) {
    changed = false
    for (const it of items) {
      if (it.fixed) continue
      const px = (it.min / remainingMin) * remainingPx
      if (px < MIN_OPL_VISIBLE_PX) {
        it.px = MIN_OPL_VISIBLE_PX
        it.fixed = true
        remainingPx  -= MIN_OPL_VISIBLE_PX
        remainingMin -= it.min
        changed = true
      }
    }
  }
  for (const it of items) {
    if (!it.fixed) {
      it.px = remainingMin > 0 ? (it.min / remainingMin) * remainingPx : MIN_OPL_VISIBLE_PX
    }
  }

  let cursor = 0
  return items.map(it => {
    const leftPx  = Math.round(cursor)
    cursor += it.px
    const widthPx = Math.round(cursor) - leftPx
    return { opl: it.opl, leftPx, widthPx }
  })
}

function expectedRowWidth(opls: AsignacionDetalleOut[], pxPerMin: number, capPx: number): number {
  const totalMin = opls.reduce((s, o) => s + (o.tiempo_planificado ?? 0), 0)
  const realPx   = totalMin * pxPerMin
  if (realPx >= capPx) return Math.max(capPx, realPx)
  return opls.reduce((s, o) => s + Math.max(MIN_OPL_VISIBLE_PX, (o.tiempo_planificado ?? 0) * pxPerMin), 0)
}

// ── Tipo para el drag ─────────────────────────────────────────────────────────

interface DraggingOpl {
  id_opl: string
  tiempo_planificado: number
  tiempo_total_teorico: number
}

// ── Overlay que recorta su contenido al viewport ──────────────────────────────
// Los hijos position:fixed se posicionan respecto a este overlay (transform lo
// convierte en bloque contenedor) y overflow:hidden impide que desborden el
// viewport y amplíen el área scrolleable del documento (scroll fantasma).
function FixedOverlay({ children }: { children: ReactNode }) {
  return createPortal(
    <div style={{
      position: 'fixed',
      inset: 0,
      overflow: 'hidden',
      pointerEvents: 'none',
      transform: 'translateZ(0)',
      zIndex: 9999,
    }}>
      {children}
    </div>,
    document.body,
  )
}

// ── Bloque OPL ────────────────────────────────────────────────────────────────

interface OplBlockProps {
  opl: AsignacionDetalleOut
  leftPx: number
  widthPx: number
  isDragging: boolean
  onDragStart: (info: DraggingOpl) => void
  onDragEnd: () => void
  onToggleFija: (opl: AsignacionDetalleOut) => void
  readonly: boolean
  matches: boolean
  searchQueryActive: boolean
}

function OplBlock({ opl, leftPx, widthPx, isDragging, onDragStart, onDragEnd, onToggleFija, readonly, matches, searchQueryActive }: OplBlockProps) {
  const [hover, setHover] = useState(false)
  const [tooltipAnchor, setTooltipAnchor] = useState({ top: 0, left: 0 })
  const [tooltipPos, setTooltipPos] = useState({ top: 0, left: 0 })
  const [blockBox, setBlockBox] = useState({ top: 0, left: 0, width: 0, height: 0 })
  const blockRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const esFija       = !!opl.es_fija
  const esArrastre   = opl.tipo_asignacion === 'arrastre'
  const color        = colorBloque(opl.tipo_asignacion)
  const planificado  = opl.tiempo_planificado ?? 0
  const totalTeorico = opl.tiempo_total_teorico ?? planificado
  const esParcial    = esParcialOpl(opl)
  const pendiente    = totalTeorico - planificado

  const handleMouseEnter = () => {
    setHover(true)
    if (blockRef.current) {
      const rect = blockRef.current.getBoundingClientRect()
      setTooltipAnchor({ top: rect.top - 8, left: rect.left + rect.width / 2 })
      setBlockBox({ top: rect.top, left: rect.left, width: rect.width, height: rect.height })
    }
  }

  // Clampa el tooltip al viewport para que no se vea cortado por el overlay.
  useLayoutEffect(() => {
    if (!hover || isDragging) return
    const el = tooltipRef.current
    if (!el) { setTooltipPos(tooltipAnchor); return }
    const margin = 8
    const half = el.offsetWidth / 2
    const h = el.offsetHeight
    let left = tooltipAnchor.left
    let top  = tooltipAnchor.top
    if (left - half < margin) left = margin + half
    if (left + half > window.innerWidth - margin) left = window.innerWidth - margin - half
    if (top - h < margin) top = h + margin
    if (top > window.innerHeight - margin) top = window.innerHeight - margin
    setTooltipPos({ top, left })
  }, [hover, isDragging, tooltipAnchor])

  // Botón 🔒 (position:fixed): clampar para que quede visible dentro del viewport.
  const BTN = 22, btnMargin = 4
  const btnCentered = widthPx < 32
  const vw = typeof window !== 'undefined' ? window.innerWidth : 0
  const vh = typeof window !== 'undefined' ? window.innerHeight : 0
  const rawBtnTop  = blockBox.top + blockBox.height / 2
  const rawBtnLeft = btnCentered ? blockBox.left + blockBox.width / 2 : blockBox.left + blockBox.width - 24
  const btnTop  = Math.min(Math.max(rawBtnTop, btnMargin + BTN / 2), vh - btnMargin - BTN / 2)
  const btnLeft = btnCentered
    ? Math.min(Math.max(rawBtnLeft, btnMargin + BTN / 2), vw - btnMargin - BTN / 2)
    : Math.min(Math.max(rawBtnLeft, btnMargin), vw - btnMargin - BTN)

  return (
    <>
    <div
      ref={blockRef}
      data-opl-id={opl.id_opl}
      draggable={!readonly && !esArrastre}
      onDragStart={e => {
        if (esArrastre) { e.preventDefault(); return }
        e.dataTransfer.effectAllowed = 'move'
        e.dataTransfer.setData('text/plain', opl.id_opl)
        setTimeout(() => onDragStart({
          id_opl: opl.id_opl,
          tiempo_planificado: planificado,
          tiempo_total_teorico: totalTeorico,
        }), 0)
      }}
      onDragEnd={onDragEnd}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setHover(false)}
      style={{
        position: 'absolute',
        left: leftPx,
        top: 4,
        width: widthPx,
        height: 'calc(100% - 8px)',
        background: color,
        borderRadius: 4,
        cursor: (readonly || esArrastre) ? 'default' : 'grab',
        opacity: isDragging ? 0.35 : (searchQueryActive && !matches ? 0.18 : 1),
        filter: searchQueryActive && !matches ? 'grayscale(0.6)' : 'none',
        boxSizing: 'border-box',
        border: (esParcial || esArrastre)
          ? '1px dashed rgba(255,255,255,0.58)'
          : '1px solid rgba(0,0,0,0.15)',
        overflow: 'visible',
        display: 'flex',
        alignItems: 'center',
        paddingLeft: 4,
        transition: 'opacity 0.15s, box-shadow 0.1s, outline 0.1s, filter 0.15s',
        boxShadow: hover && !isDragging ? '0 2px 8px rgba(0,0,0,0.2)' : 'none',
        userSelect: 'none',
        zIndex: hover ? 2 : (searchQueryActive && matches ? 2 : 1),
      }}
    >
      <span style={{
        fontSize: 10,
        color: '#fff',
        fontWeight: 600,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        lineHeight: 1.2,
        flex: 1,
        minWidth: 0,
        pointerEvents: 'none',
      }}>
        {prefixOpl(opl)}{opl.id_opl}
      </span>
      {!readonly && !esArrastre && hover && (
        <FixedOverlay>
          <button
            onMouseDown={e => e.stopPropagation()}
            onClick={e => {
              e.stopPropagation()
              e.preventDefault()
              onToggleFija(opl)
            }}
            title={esFija ? 'Quitar fija' : 'Marcar como fija'}
            style={{
              position: 'fixed',
              top: btnTop,
              left: btnLeft,
              transform: 'translateY(-50%)' + (btnCentered ? ' translateX(-50%)' : ''),
              width: 22,
              height: 22,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(15,23,42,0.78)',
              border: '1.5px solid rgba(255,255,255,0.45)',
              borderRadius: 5,
              color: '#fff',
              fontSize: 12,
              padding: 0,
              cursor: 'pointer',
              lineHeight: 1,
              pointerEvents: 'auto',
              boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
            }}
          >
            {esFija ? '🔓' : '🔒'}
          </button>
        </FixedOverlay>
      )}
      {esFija && !esArrastre && (!hover || readonly) && (
        <span style={{
          position: 'absolute',
          bottom: 2,
          right: 3,
          fontSize: 9,
          lineHeight: 1,
          color: '#fff',
          pointerEvents: 'none',
          userSelect: 'none',
        }}>🔒</span>
      )}
    </div>

    {hover && !isDragging && (
      <FixedOverlay>
      <div ref={tooltipRef} style={{
        position: 'fixed',
        top: tooltipPos.top,
        left: tooltipPos.left,
        transform: 'translate(-50%, -100%)',
        background: 'rgba(17,24,39,0.96)',
        color: '#fff',
        borderRadius: 6,
        padding: '7px 10px',
        fontSize: 11,
        whiteSpace: 'nowrap',
        pointerEvents: 'none',
        boxShadow: '0 4px 12px rgba(0,0,0,0.35)',
        lineHeight: 1.6,
        minWidth: 160,
      }}>
        <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 2 }}>{opl.id_opl}</div>
        <div style={{ color: '#d1d5db' }}>{opl.ref_articulo}{opl.nombre_articulo ? ` · ${opl.nombre_articulo}` : ''}</div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, marginTop: 4 }}>
          <span style={{ fontWeight: 700, fontSize: 11, color: esArrastre ? '#a78bfa' : opl.tipo_asignacion === 'obligatoria' ? '#f87171' : '#60a5fa' }}>
            {esArrastre ? 'Arrastre' : opl.tipo_asignacion === 'obligatoria' ? 'Obligatoria' : 'Normal'}
          </span>
          {esArrastre && <span style={{ fontSize: 11 }}>⚓</span>}
          {esFija && !esArrastre && <span style={{ fontSize: 11 }}>🔒</span>}
        </div>
        {esArrastre ? (
          <>
            <div style={{ marginTop: 3 }}>Esta semana: <b>{planificado.toFixed(0)} min</b></div>
            <div style={{ color: '#9ca3af' }}>Semana anterior: {(totalTeorico - planificado).toFixed(0)} min</div>
          </>
        ) : esParcial ? (
          <>
            <div style={{ marginTop: 3 }}>Asignado: <b>{planificado.toFixed(0)} min</b></div>
            <div style={{ color: '#9ca3af' }}>Restante: {pendiente.toFixed(0)} min</div>
          </>
        ) : (
          <div>{planificado.toFixed(0)} min</div>
        )}
      </div>
      </FixedOverlay>
    )}
    </>
  )
}

// ── Chip OPL sin asignar ──────────────────────────────────────────────────────

interface SinAsignarOplChipProps {
  opl: AsignacionDetalleOut
  isDragging: boolean
  onDragStart: (e: React.DragEvent) => void
  onDragEnd: () => void
  readonly: boolean
  matches: boolean
  searchQueryActive: boolean
}

function SinAsignarOplChip({ opl, isDragging, onDragStart, onDragEnd, readonly, matches, searchQueryActive }: SinAsignarOplChipProps) {
  const [hover, setHover] = useState(false)
  const [tooltipAnchor, setTooltipAnchor] = useState({ top: 0, left: 0 })
  const [tooltipPos, setTooltipPos] = useState({ top: 0, left: 0 })
  const chipRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const esArrastre   = opl.tipo_asignacion === 'arrastre'
  const planificado  = opl.tiempo_planificado ?? 0
  const totalTeorico = opl.tiempo_total_teorico ?? planificado
  const esParcial    = (totalTeorico - planificado) > 0.5
  const pendiente    = totalTeorico - planificado

  const handleMouseEnter = () => {
    setHover(true)
    if (chipRef.current) {
      const rect = chipRef.current.getBoundingClientRect()
      setTooltipAnchor({ top: rect.top - 8, left: rect.left + rect.width / 2 })
    }
  }

  // Clampa el tooltip al viewport para que no se vea cortado por el overlay.
  useLayoutEffect(() => {
    if (!hover || isDragging) return
    const el = tooltipRef.current
    if (!el) { setTooltipPos(tooltipAnchor); return }
    const margin = 8
    const half = el.offsetWidth / 2
    const h = el.offsetHeight
    let left = tooltipAnchor.left
    let top  = tooltipAnchor.top
    if (left - half < margin) left = margin + half
    if (left + half > window.innerWidth - margin) left = window.innerWidth - margin - half
    if (top - h < margin) top = h + margin
    if (top > window.innerHeight - margin) top = window.innerHeight - margin
    setTooltipPos({ top, left })
  }, [hover, isDragging, tooltipAnchor])

  return (
    <>
      <div
        ref={chipRef}
        data-opl-id={opl.id_opl}
        draggable={!readonly && !esArrastre}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setHover(false)}
        style={{
          padding: '3px 8px', borderRadius: 4,
          background: opl.tipo_asignacion === 'obligatoria' ? '#dc2626' : '#2563eb', color: '#fff',
          fontSize: 11, fontWeight: 600,
          cursor: (readonly || esArrastre) ? 'default' : 'grab',
          opacity: isDragging ? 0.4 : (searchQueryActive && !matches ? 0.18 : 1),
          filter: searchQueryActive && !matches ? 'grayscale(0.6)' : 'none',
          userSelect: 'none',
          border: esArrastre ? '2px dashed rgba(0,0,0,0.3)' : 'none',
          boxShadow: hover && !isDragging ? '0 2px 8px rgba(0,0,0,0.2)' : 'none',
          transition: 'box-shadow 0.1s, opacity 0.15s, outline 0.1s, filter 0.15s',
        }}
      >
        {prefixOpl(opl)}{opl.id_opl}
      </div>

      {hover && !isDragging && (
        <FixedOverlay>
        <div ref={tooltipRef} style={{
          position: 'fixed',
          top: tooltipPos.top,
          left: tooltipPos.left,
          transform: 'translate(-50%, -100%)',
          background: 'rgba(17,24,39,0.96)',
          color: '#fff',
          borderRadius: 6,
          padding: '7px 10px',
          fontSize: 11,
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.35)',
          lineHeight: 1.6,
          minWidth: 160,
        }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 2 }}>{opl.id_opl}</div>
          <div style={{ color: '#d1d5db' }}>{opl.ref_articulo}{opl.nombre_articulo ? ` · ${opl.nombre_articulo}` : ''}</div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, marginTop: 4 }}>
            <span style={{ fontWeight: 700, fontSize: 11, color: esArrastre ? '#a78bfa' : opl.tipo_asignacion === 'obligatoria' ? '#f87171' : '#60a5fa' }}>
              {esArrastre ? 'Arrastre' : opl.tipo_asignacion === 'obligatoria' ? 'Obligatoria' : 'Normal'}
            </span>
            {esArrastre && <span style={{ fontSize: 11 }}>⚓</span>}
          </div>
          {esArrastre ? (
            <>
              <div style={{ marginTop: 3 }}>Esta semana: <b>{planificado.toFixed(0)} min</b></div>
              <div style={{ color: '#9ca3af' }}>Semana anterior: {pendiente.toFixed(0)} min</div>
            </>
          ) : esParcial ? (
            <>
              <div style={{ marginTop: 3 }}>Planificado: <b>{planificado.toFixed(0)} min</b></div>
              <div style={{ color: '#9ca3af' }}>Restante: {pendiente.toFixed(0)} min</div>
            </>
          ) : (
            <div style={{ marginTop: 3 }}>{planificado.toFixed(0)} min</div>
          )}
        </div>
        </FixedOverlay>
      )}
    </>
  )
}

// ── Ordenación de OPLs por fila ───────────────────────────────────────────────

function sortOpls(opls: AsignacionDetalleOut[]): AsignacionDetalleOut[] {
  const arrastreLst = opls.filter(o => o.tipo_asignacion === 'arrastre')
  const parcialLst  = opls.filter(o => o.tipo_asignacion !== 'arrastre' && esParcialOpl(o))
  const rest        = opls.filter(o => o.tipo_asignacion !== 'arrastre' && !esParcialOpl(o))

  const byFamilia: Record<string, AsignacionDetalleOut[]> = {}
  for (const o of rest) {
    const fam = o.ref_familia || '__'
    if (!byFamilia[fam]) byFamilia[fam] = []
    byFamilia[fam]!.push(o)
  }
  for (const g of Object.values(byFamilia)) {
    g.sort((a, b) => (b.tiempo_planificado ?? 0) - (a.tiempo_planificado ?? 0))
  }
  const sortedGroups = Object.values(byFamilia).sort((gA, gB) => {
    const maxA = Math.max(...gA.map(o => o.tiempo_planificado ?? 0))
    const maxB = Math.max(...gB.map(o => o.tiempo_planificado ?? 0))
    return maxB - maxA
  })
  parcialLst.sort((a, b) => (b.tiempo_planificado ?? 0) - (a.tiempo_planificado ?? 0))

  return [...arrastreLst, ...sortedGroups.flat(), ...parcialLst]
}

// ── Fila de operario ──────────────────────────────────────────────────────────

interface FilaOperarioProps {
  operario: OperarioOut
  opls: AsignacionDetalleOut[]
  contentWidthPx: number
  pxPerMin: number
  draggingOpl: DraggingOpl | null
  onDragStart: (info: DraggingOpl) => void
  onDragEnd: () => void
  onDrop: (idOpl: string, dni: string) => void
  onToggleFija: (opl: AsignacionDetalleOut) => void
  readonly: boolean
  searchQuery: string
}

function FilaOperario({ operario, opls, contentWidthPx, pxPerMin, draggingOpl, onDragStart, onDragEnd, onDrop, onToggleFija, readonly, searchQuery }: FilaOperarioProps) {
  const [isOver, setIsOver]         = useState(false)
  const [overCursor, setOverCursor] = useState(false)

  const sorted = sortOpls(opls)
  const capacidadMin = Math.round(operario.horas_semanales * 60)
  const totalMin     = opls.reduce((s, o) => s + (o.tiempo_planificado ?? 0), 0)
  const pct          = capacidadMin > 0 ? Math.min(100, Math.round((totalMin / capacidadMin) * 100)) : 0
  const capWidthPx   = capacidadMin * pxPerMin
  const empaquetado  = packPx(sorted, pxPerMin, capWidthPx)

  function cabe(dragging: DraggingOpl | null): boolean {
    if (!dragging) return true
    const yaEsta = opls.some(o => o.id_opl === dragging.id_opl)
    if (yaEsta) return true
    const consumoDestino = dragging.tiempo_total_teorico || dragging.tiempo_planificado
    return totalMin + consumoDestino <= capacidadMin + 0.01
  }

  const isDragging = !!draggingOpl
  const cabeAqui   = cabe(draggingOpl)

  return (
    <div style={{
      display: 'flex',
      alignItems: 'stretch',
      minHeight: 52,
      borderBottom: '1px solid var(--border, #e5e7eb)',
    }}>
      {/* Etiqueta sticky */}
      <div style={{
        width: LABEL_COL_PX, minWidth: LABEL_COL_PX, flexShrink: 0,
        padding: '6px 12px',
        borderRight: '1px solid var(--border, #e5e7eb)',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        background: 'var(--bg-card, #fff)',
        position: 'sticky',
        left: 0,
        zIndex: 3,
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text, #111)', lineHeight: 1.3 }}>
          {operario.nombre_completo ?? operario.dni}
        </div>
        <div style={{ fontSize: 11, marginTop: 2, color: 'var(--text-muted, #6b7280)' }}>
          {totalMin.toFixed(0)} / {capacidadMin} min ({pct}%)
        </div>
      </div>

      {/* Track de timeline con ancho fijo */}
      <div style={{ position: 'relative', width: contentWidthPx, minWidth: contentWidthPx, flexShrink: 0 }}>
        {/* Barra de capacidad guía */}
        <div style={{
          position: 'absolute',
          left: 0, top: '50%', transform: 'translateY(-50%)',
          width: capWidthPx,
          height: 8,
          background: 'var(--border, #e5e7eb)',
          borderRadius: 4,
          zIndex: 0,
        }} />

        {empaquetado.map(({ opl, leftPx, widthPx }) => (
          <OplBlock
            key={opl.id_opl}
            opl={opl}
            leftPx={leftPx}
            widthPx={widthPx}
            isDragging={draggingOpl?.id_opl === opl.id_opl}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            onToggleFija={onToggleFija}
            readonly={readonly}
            matches={matchesQuery(opl, searchQuery)}
            searchQueryActive={searchQuery.trim() !== ''}
          />
        ))}

        {isDragging && (
          <div
            onDragOver={e => {
              if (!cabeAqui) {
                e.dataTransfer.dropEffect = 'none'
                setIsOver(false)
                setOverCursor(true)
                return
              }
              e.preventDefault()
              e.dataTransfer.dropEffect = 'move'
              setIsOver(true)
              setOverCursor(false)
            }}
            onDragLeave={() => { setIsOver(false); setOverCursor(false) }}
            onDrop={e => {
              e.preventDefault()
              setIsOver(false)
              setOverCursor(false)
              if (!cabeAqui) return
              const idOpl = e.dataTransfer.getData('text/plain')
              if (idOpl) onDrop(idOpl, operario.dni)
              onDragEnd()
            }}
            style={{
              position: 'absolute', inset: 0,
              zIndex: 10,
              cursor: cabeAqui ? 'copy' : 'not-allowed',
              background: isOver
                ? 'rgba(37,99,235,0.12)'
                : overCursor
                  ? 'rgba(239,68,68,0.35)'
                  : 'transparent',
              border: overCursor ? '2px solid rgba(239,68,68,0.7)' : 'none',
              transition: 'background 0.1s',
              borderRadius: 0,
            }}
          />
        )}
      </div>
    </div>
  )
}

// ── Componente principal ──────────────────────────────────────────────────────

export interface LimpiarOpts {
  desfijar: boolean
  normalizar_obligatorias: boolean
  eliminar_arrastre: boolean
}

interface Props {
  asignaciones: AsignacionDetalleOut[]
  operarios: OperarioOut[]
  onDrop: (idOpl: string, dni: string | null) => void
  onToggleFija: (opl: AsignacionDetalleOut) => void
  readonly: boolean
  onExportExcel: () => void
  onReoptimize: () => void
  onLimpiarSelectivo: (opts: LimpiarOpts) => Promise<void>
  oplsSinReparto: OplOut[]
  onAddOpls: (ids: string[]) => Promise<void>
  articulosByRef?: Map<string, string>
}

/**
 * Tablero de asignaciones por operario con drag & drop.
 *
 * Permite mover OPLs entre operarios, fijar/desfijar asignaciones, reoptimizar,
 * limpiar selectivamente, añadir OPLs sin repartir y exportar a Excel. En modo
 * `readonly` solo muestra el reparto sin permitir cambios.
 * @param asignaciones Asignaciones actuales a pintar.
 * @param operarios Operarios (columnas del tablero).
 * @param onDrop Callback al soltar una OPL sobre un operario.
 * @param onToggleFija Callback para fijar/desfijar una asignación.
 * @param readonly Si el tablero es de solo lectura (reparto aprobado).
 * @param onExportExcel Exporta el reparto a Excel.
 * @param onReoptimize Relanza la optimización.
 * @param onLimpiarSelectivo Aplica una limpieza selectiva.
 * @param oplsSinReparto OPLs disponibles para añadir al reparto.
 * @param onAddOpls Añade OPLs seleccionadas al reparto.
 * @param articulosByRef Mapa referencia→nombre de artículo.
 */
export default function TimelineBoard({ asignaciones, operarios, onDrop, onToggleFija, readonly, onExportExcel, onReoptimize, onLimpiarSelectivo, oplsSinReparto, onAddOpls, articulosByRef }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [draggingOpl, setDraggingOpl] = useState<DraggingOpl | null>(null)
  const [sinAsignarOver, setSinAsignarOver] = useState(false)
  const [viewportWidth, setViewportWidth] = useState(1200)
  const [zoom, setZoom] = useState<number>(() => {
    const saved = Number(localStorage.getItem(ZOOM_KEY))
    return Number.isFinite(saved) && saved >= ZOOM_MIN && saved <= ZOOM_MAX ? saved : 1
  })
  const [showReoptimizeConfirm, setShowReoptimizeConfirm] = useState(false)
  const [showLimpiarModal, setShowLimpiarModal] = useState(false)
  const [limpiarDesfijar, setLimpiarDesfijar] = useState(false)
  const [limpiarNormalizar, setLimpiarNormalizar] = useState(false)
  const [limpiarArrastre, setLimpiarArrastre] = useState(false)
  const [limpiarLoading, setLimpiarLoading] = useState(false)
  const [showAddOplsModal, setShowAddOplsModal] = useState(false)
  const [addOplsSelected, setAddOplsSelected] = useState<string[]>([])
  const [addOplsSubmitting, setAddOplsSubmitting] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [activeIdx, setActiveIdx] = useState(0)
  const [sectionCollapsed, setSectionCollapsed] = useState<{ opl: boolean; articulo: boolean; familia: boolean }>({
    opl: false, articulo: false, familia: false,
  })
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0, width: 0 })
  const searchWrapperRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    localStorage.setItem(ZOOM_KEY, String(zoom))
  }, [zoom])

  // Inyecta los estilos globales del buscador una sola vez
  useEffect(() => {
    if (document.getElementById('opl-search-styles')) return
    const el = document.createElement('style')
    el.id = 'opl-search-styles'
    el.textContent = `
      @keyframes oplSearchPopIn {
        from { opacity: 0; transform: translateY(-6px) scale(0.985); }
        to   { opacity: 1; transform: translateY(0)     scale(1);     }
      }
      .opl-search-pop {
        animation: oplSearchPopIn 140ms cubic-bezier(0.16, 1, 0.3, 1);
        transform-origin: top center;
      }
      .opl-sug-row:hover { background: rgba(37,99,235,0.06) !important; }
      .opl-sug-scroll::-webkit-scrollbar { width: 8px; }
      .opl-sug-scroll::-webkit-scrollbar-thumb { background: rgba(107,114,128,0.3); border-radius: 4px; }
      .opl-sug-scroll::-webkit-scrollbar-thumb:hover { background: rgba(107,114,128,0.5); }
    `
    document.head.appendChild(el)
  }, [])

  useEffect(() => {
    if (!showSuggestions) return
    function handleClick(e: MouseEvent) {
      const target = e.target as Node | null
      // Ignora clicks dentro del wrapper del input o del dropdown (incluye scrollbar)
      if (searchWrapperRef.current && searchWrapperRef.current.contains(target)) return
      if (target instanceof Element && target.closest('.opl-search-pop')) return
      setShowSuggestions(false)
    }
    // Cierra el dropdown si se hace scroll en cualquier ancestro o en window
    function handleScroll(e: Event) {
      const target = e.target as Node | null
      // Ignora el scroll interno del propio listbox
      if (target instanceof Element && target.closest('.opl-search-pop')) return
      setShowSuggestions(false)
    }
    document.addEventListener('mousedown', handleClick)
    window.addEventListener('scroll', handleScroll, true)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [showSuggestions])

  useEffect(() => {
    if (!scrollRef.current) return
    const el = scrollRef.current
    const observer = new ResizeObserver(entries => {
      const entry = entries[0]
      if (!entry) return
      setViewportWidth(entry.contentRect.width)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // Mantiene visible la sugerencia activa al navegar con teclado
  useEffect(() => {
    if (!showSuggestions) return
    const el = document.getElementById(`opl-sug-${activeIdx}`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [activeIdx, showSuggestions])

  const trimmedQuery = searchQuery.trim()

  // Sugerencias autocomplete (memoizadas, antes del early return para no romper rules-of-hooks)
  const { suggestOpls, suggestArticulos, suggestFamilias, flatSuggestions } = useMemo(() => {
    if (!asignaciones) return { suggestOpls: [], suggestArticulos: [], suggestFamilias: [], flatSuggestions: [] as Suggestion[] }
    const needle = trimmedQuery.toLowerCase()
    const collator = new Intl.Collator('es', { sensitivity: 'base', numeric: true })
    const allOplIds = [...new Set(asignaciones.map(a => a.id_opl))]
    const opls = allOplIds
      .filter(id => !needle || id.toLowerCase().includes(needle))
      .sort(collator.compare)
    const articuloMap = new Map<string, string>()
    for (const a of asignaciones) {
      if (a.ref_articulo && !articuloMap.has(a.ref_articulo))
        articuloMap.set(a.ref_articulo, a.nombre_articulo ?? '')
    }
    const arts = [...articuloMap.entries()]
      .filter(([ref, nombre]) => !needle || ref.toLowerCase().includes(needle) || nombre.toLowerCase().includes(needle))
      .sort(([refA], [refB]) => collator.compare(refA, refB))
    const fams = [...new Set(asignaciones.filter(a => a.ref_familia).map(a => a.ref_familia!))]
      .filter(f => !needle || f.toLowerCase().includes(needle))
      .sort(collator.compare)
    const flat: Suggestion[] = [
      ...(sectionCollapsed.opl ? [] : opls.map<Suggestion>(id => ({ kind: 'opl', value: id }))),
      ...(sectionCollapsed.articulo ? [] : arts.map<Suggestion>(([ref, nombre]) => ({ kind: 'articulo', value: ref, nombre }))),
      ...(sectionCollapsed.familia ? [] : fams.map<Suggestion>(ref => ({ kind: 'familia', value: ref }))),
    ]
    return { suggestOpls: opls, suggestArticulos: arts, suggestFamilias: fams, flatSuggestions: flat }
  }, [asignaciones, trimmedQuery, sectionCollapsed])

  const firstMatchIdOpl = useMemo(() => {
    if (!asignaciones || !trimmedQuery) return null
    for (const a of asignaciones) {
      if (matchesQuery(a, trimmedQuery)) return a.id_opl
    }
    return null
  }, [asignaciones, trimmedQuery])

  if (!asignaciones || !operarios) return null

  const operariosActivos = operarios.filter(op => op.horas_semanales > 0)

  const maxCapMin = Math.max(
    ...operariosActivos.map(op => Math.round(op.horas_semanales * 60)),
    1,
  )

  const porOperario: Record<string, AsignacionDetalleOut[]> = {}
  const sinAsignar: AsignacionDetalleOut[] = []
  for (const a of asignaciones) {
    if (a.dni_operario) {
      if (!porOperario[a.dni_operario]) porOperario[a.dni_operario] = []
      porOperario[a.dni_operario]!.push(a)
    } else {
      sinAsignar.push(a)
    }
  }

  const availableWidth = Math.max(200, viewportWidth - LABEL_COL_PX)
  const fitPxPerMin = availableWidth / maxCapMin
  const pxPerMin = fitPxPerMin * zoom
  const maxCapPx = maxCapMin * pxPerMin

  // ancho real = máximo entre capacidad y el operario más extendido (cubre sobrecargas e inflaciones por min-width)
  const maxPackedPx = Math.max(
    maxCapPx,
    ...operariosActivos.map(op => {
      const opls = porOperario[op.dni] ?? []
      const capPxRow = Math.round(op.horas_semanales * 60) * pxPerMin
      return expectedRowWidth(opls, pxPerMin, capPxRow)
    }),
  )
  const contentWidthPx = Math.max(maxPackedPx, 200)

  // Time axis ticks aligned to pixel scale
  const tickStepMin = maxCapMin <= 240 ? 30 : maxCapMin <= 600 ? 60 : 120
  const ticks: number[] = []
  for (let t = 0; t <= maxCapMin; t += tickStepMin) ticks.push(t)

  const matchCount = trimmedQuery
    ? asignaciones.filter(a => matchesQuery(a, trimmedQuery)).length
    : 0

  const hasSuggestions = flatSuggestions.length > 0
  const hasAnySection = suggestOpls.length > 0 || suggestArticulos.length > 0 || suggestFamilias.length > 0
  const safeActiveIdx = Math.min(activeIdx, Math.max(0, flatSuggestions.length - 1))

  function openSuggestions() {
    if (searchWrapperRef.current) {
      const rect = searchWrapperRef.current.getBoundingClientRect()
      setDropdownPos({ top: rect.bottom + 6, left: rect.left, width: rect.width })
    }
    setShowSuggestions(true)
  }

  function pickSuggestion(value: string) {
    setSearchQuery(value)
    setShowSuggestions(false)
    setActiveIdx(0)
    // Tras seleccionar sugerencia, salta al primer match del nuevo query
    requestAnimationFrame(() => jumpToOpl(findFirstMatchId(value)))
  }

  function findFirstMatchId(q: string): string | null {
    const trimmed = q.trim()
    if (!trimmed) return null
    for (const a of asignaciones) {
      if (matchesQuery(a, trimmed)) return a.id_opl
    }
    return null
  }

  function jumpToOpl(idOpl: string | null) {
    if (!idOpl) return
    const el = document.querySelector(`[data-opl-id="${CSS.escape(idOpl)}"]`) as HTMLElement | null
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
  }

  function handleSearchKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Escape') {
      if (showSuggestions) {
        setShowSuggestions(false)
      } else if (searchQuery) {
        setSearchQuery('')
      } else {
        searchInputRef.current?.blur()
      }
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (!showSuggestions && hasSuggestions) { openSuggestions(); return }
      if (flatSuggestions.length > 0) {
        setActiveIdx(i => (i + 1) % flatSuggestions.length)
      }
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (!showSuggestions && hasSuggestions) { openSuggestions(); setActiveIdx(flatSuggestions.length - 1); return }
      if (flatSuggestions.length > 0) {
        setActiveIdx(i => (i - 1 + flatSuggestions.length) % flatSuggestions.length)
      }
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      // Enter siempre busca el string literal escrito, no la sugerencia activa
      setShowSuggestions(false)
      jumpToOpl(firstMatchIdOpl)
    }
  }

  const leyendaTipos = [
    { color: '#2563eb', label: 'Normal' },
    { color: '#dc2626', label: 'Obligatoria' },
    { color: '#5b21b6', label: '⚓ Arrastre', border: '1px dashed rgba(255,255,255,0.58)' },
  ]

  function handleDragEnd() {
    setDraggingOpl(null)
    setSinAsignarOver(false)
  }

  const zoomIn = () => setZoom(z => Math.min(ZOOM_MAX, z * ZOOM_STEP))
  const zoomOut = () => setZoom(z => Math.max(ZOOM_MIN, z / ZOOM_STEP))
  const zoomFit = () => setZoom(1)

  const nNoFijas = asignaciones.filter(
    a => !a.es_fija && a.dni_operario && a.tipo_asignacion !== 'arrastre'
  ).length

  function handleReoptimizeClick() {
    if (nNoFijas > 0) {
      setShowReoptimizeConfirm(true)
    } else {
      onReoptimize()
    }
  }

  async function handleLimpiarConfirm() {
    if (!limpiarDesfijar && !limpiarNormalizar && !limpiarArrastre) return
    setLimpiarLoading(true)
    try {
      await onLimpiarSelectivo({ desfijar: limpiarDesfijar, normalizar_obligatorias: limpiarNormalizar, eliminar_arrastre: limpiarArrastre })
    } finally {
      setLimpiarLoading(false)
      setShowLimpiarModal(false)
      setLimpiarDesfijar(false)
      setLimpiarNormalizar(false)
      setLimpiarArrastre(false)
    }
  }

  return (
    <>
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Cabecera */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border, #e5e7eb)',
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      }}>
        <div className="card-title" style={{ margin: 0, marginRight: 4 }}>Distribución semanal</div>

        {/* Leyenda */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {leyendaTipos.map(l => (
            <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
              <div style={{ width: 12, height: 12, borderRadius: 2, background: l.color, flexShrink: 0, border: l.border ?? '1px solid rgba(0,0,0,0.15)' }} />
              {l.label}
            </div>
          ))}
          <div style={{ width: 1, height: 14, background: 'var(--border, #e5e7eb)', flexShrink: 0 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
            <div style={{ width: 12, height: 12, borderRadius: 2, background: '#2563eb', flexShrink: 0, border: '1px dashed rgba(255,255,255,0.58)' }} />
            Parcial
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-muted)' }}>
            <span style={{ width: 12, height: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 10 }}>🔒</span>
            Fijada
          </div>
        </div>

        {/* Wrapper derecho: marginLeft auto lo pega a la derecha; flexWrap+flex-end mantiene los bloques a la derecha al saltar */}
        <div style={{ marginLeft: 'auto', display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', alignItems: 'center', gap: 10 }}>

        {/* Buscador de OPLs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <div ref={searchWrapperRef} style={{ position: 'relative' }}>
            {/* Icono lupa */}
            <div style={{
              position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: showSuggestions ? '#2563eb' : 'var(--text-muted, #9ca3af)',
              pointerEvents: 'none',
              transition: 'color 0.15s',
            }}>
              <IconSearch size={13} />
            </div>

            <input
              ref={searchInputRef}
              type="text"
              role="combobox"
              aria-expanded={showSuggestions}
              aria-controls="opl-search-suggestions"
              aria-activedescendant={showSuggestions && hasSuggestions ? `opl-sug-${safeActiveIdx}` : undefined}
              value={searchQuery}
              onChange={e => { setSearchQuery(e.target.value); setActiveIdx(0); openSuggestions() }}
              onFocus={openSuggestions}
              onKeyDown={handleSearchKeyDown}
              placeholder="Buscar OPL, artículo o familia"
              style={{
                height: 30,
                padding: searchQuery ? '0 30px 0 28px' : '0 12px 0 28px',
                fontSize: 12.5,
                borderRadius: 7,
                border: `1px solid ${showSuggestions ? '#2563eb' : 'var(--border, #e5e7eb)'}`,
                background: 'var(--surface, #fff)',
                color: 'var(--text, #111827)',
                width: 260,
                outline: 'none',
                boxShadow: showSuggestions
                  ? '0 0 0 3px rgba(37,99,235,0.12)'
                  : 'inset 0 1px 0 rgba(0,0,0,0.02)',
                transition: 'border-color 0.15s, box-shadow 0.18s',
                fontFamily: 'ui-sans-serif, system-ui, sans-serif',
              }}
            />

            {/* Botón limpiar */}
            {searchQuery && (
              <button
                onMouseDown={e => e.preventDefault()}
                onClick={() => { setSearchQuery(''); setActiveIdx(0); setShowSuggestions(false); searchInputRef.current?.focus() }}
                title="Limpiar búsqueda"
                aria-label="Limpiar búsqueda"
                style={{
                  position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)',
                  width: 20, height: 20,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'rgba(107,114,128,0.12)',
                  border: 'none', borderRadius: 5, cursor: 'pointer',
                  color: 'var(--text-muted, #6b7280)',
                  transition: 'background 0.12s, color 0.12s',
                  padding: 0,
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLButtonElement).style.background = 'rgba(220,38,38,0.12)'
                  ;(e.currentTarget as HTMLButtonElement).style.color = '#dc2626'
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLButtonElement).style.background = 'rgba(107,114,128,0.12)'
                  ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted, #6b7280)'
                }}
              >
                <IconX size={11} />
              </button>
            )}
          </div>

          <div style={{ width: 1, height: 20, background: 'var(--border, #e5e7eb)' }} />
        </div>

        {/* Bloque 1: hint + zoom — salta junto */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0, flexWrap: 'nowrap' }}>
          {!readonly && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
              Arrastra · 🔒 fijar/desfijar
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'var(--bg-subtle, #f9fafb)', border: '1px solid var(--border, #e5e7eb)', borderRadius: 6, padding: '3px 6px', fontSize: 12 }}>
            <button onClick={zoomOut} style={{ border: '1px solid var(--border, #e5e7eb)', background: '#fff', borderRadius: 4, padding: '1px 6px', cursor: 'pointer', fontSize: 12 }} title="Alejar">−</button>
            <button onClick={zoomFit} disabled={zoom === 1} style={{ border: '1px solid var(--border, #e5e7eb)', background: zoom === 1 ? 'var(--bg-subtle, #f9fafb)' : '#fff', borderRadius: 4, padding: '1px 6px', cursor: zoom === 1 ? 'default' : 'pointer', fontSize: 12 }} title="Ajustar">Ajustar</button>
            <button onClick={zoomIn} style={{ border: '1px solid var(--border, #e5e7eb)', background: '#fff', borderRadius: 4, padding: '1px 6px', cursor: 'pointer', fontSize: 12 }} title="Acercar">+</button>
            <div style={{ minWidth: 38, textAlign: 'right', color: 'var(--text-muted)', fontSize: 11 }}>{Math.round(zoom * 100)}%</div>
          </div>
          <div style={{ width: 1, height: 20, background: 'var(--border, #e5e7eb)' }} />
        </div>

        {/* Bloque 2: botones de acción — salta junto */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0, flexWrap: 'nowrap' }}>
          {/* negro=exportar · verde=añadir · gris=recalcular · rojo=destructivo */}
          <button
            onClick={onExportExcel}
            title="Exportar reparto a Excel"
            style={{
              height: 28, padding: '0 10px', fontSize: 12, borderRadius: 5,
              background: 'var(--accent, #111827)', color: '#fff', border: 'none',
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            ↓ Excel
          </button>
          {!readonly && (
            <>
              {oplsSinReparto.length > 0 && (
                <button
                  onClick={() => { setAddOplsSelected([]); setShowAddOplsModal(true) }}
                  title="Añadir OPLs sin reparto a sin asignar"
                  style={{
                    height: 28, padding: '0 10px', fontSize: 12, borderRadius: 5,
                    background: 'transparent', border: '1px solid #6ee7b7',
                    color: '#059669', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 5,
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = '#f0fdf4' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent' }}
                >
                  + OPLs
                </button>
              )}
              <button
                onClick={handleReoptimizeClick}
                style={{
                  height: 28, padding: '0 10px', fontSize: 12, borderRadius: 5,
                  background: 'transparent', border: '1px solid var(--border, #e5e7eb)',
                  color: 'var(--text-muted, #6b7280)', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 5,
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = '#9ca3af'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--text, #111827)' }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border, #e5e7eb)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted, #6b7280)' }}
              >
                ↺ Re-optimizar
              </button>
              <button
                onClick={() => { setShowLimpiarModal(true) }}
                style={{
                  height: 28, padding: '0 10px', fontSize: 12, borderRadius: 5,
                  background: 'transparent', border: '1px solid #fca5a5',
                  color: '#dc2626', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 5,
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = '#fef2f2' }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent' }}
              >
                ⊘ Limpiar
              </button>
            </>
          )}
        </div>

        </div>{/* /wrapper derecho */}
      </div>

      {/* Contenedor con scroll horizontal — eje + filas + sin asignar se mueven juntos */}
      <div ref={scrollRef} style={{ overflowX: 'auto' }}>

        {/* Eje de tiempo */}
        <div style={{
          display: 'flex',
          alignItems: 'stretch',
          borderBottom: '1px solid var(--border, #e5e7eb)',
          background: 'var(--bg-subtle, #f9fafb)',
        }}>
          <div style={{
            width: LABEL_COL_PX, minWidth: LABEL_COL_PX, flexShrink: 0,
            padding: '4px 12px', fontSize: 11, color: 'var(--text-muted)',
            borderRight: '1px solid var(--border, #e5e7eb)',
            position: 'sticky',
            left: 0,
            zIndex: 3,
            background: 'var(--bg-subtle, #f9fafb)',
          }}>
            Operario
          </div>
          <div style={{ position: 'relative', width: contentWidthPx, minWidth: contentWidthPx, height: 22, flexShrink: 0 }}>
            {ticks.map(tickMin => (
              <div key={tickMin} style={{
                position: 'absolute',
                left: tickMin * pxPerMin,
                top: 0,
                fontSize: 10,
                color: 'var(--text-muted)',
                transform: tickMin === maxCapMin ? 'translateX(-100%)' : tickMin > 0 ? 'translateX(-50%)' : 'none',
                paddingTop: 4,
                whiteSpace: 'nowrap',
              }}>
                {tickMin >= 60 || tickMin === 0
                  ? `${Math.floor(tickMin / 60)}h${tickMin % 60 ? `${tickMin % 60}m` : ''}`
                  : `${tickMin}min`}
              </div>
            ))}
          </div>
        </div>

        {/* Filas de operarios */}
        {operariosActivos.map(op => (
          <FilaOperario
            key={op.dni}
            operario={op}
            opls={porOperario[op.dni] ?? []}
            contentWidthPx={contentWidthPx}
            pxPerMin={pxPerMin}
            draggingOpl={draggingOpl}
            onDragStart={setDraggingOpl}
            onDragEnd={handleDragEnd}
            onDrop={onDrop}
            onToggleFija={onToggleFija}
            readonly={readonly}
            searchQuery={searchQuery}
          />
        ))}

      </div>

      {/* Fila "Sin asignar" — fuera del scroll para no moverse horizontalmente */}
      <div style={{
        display: 'flex', alignItems: 'stretch', minHeight: 48,
        background: sinAsignarOver ? 'rgba(156,163,175,0.12)' : 'transparent',
        transition: 'background 0.1s',
        position: 'relative',
        borderTop: '1px solid var(--border, #e5e7eb)',
      }}>
        <div style={{
          width: LABEL_COL_PX, minWidth: LABEL_COL_PX, flexShrink: 0,
          padding: '6px 12px',
          borderRight: '1px solid var(--border, #e5e7eb)',
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          background: 'var(--bg-card, #fff)',
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted, #6b7280)' }}>Sin asignar</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted, #9ca3af)', marginTop: 2 }}>
            {sinAsignar.length} OPL{sinAsignar.length !== 1 ? 's' : ''}
          </div>
        </div>

        <div
          style={{
            display: 'flex', alignItems: 'center',
            padding: '4px 12px', gap: 6, flexWrap: 'wrap',
            position: 'relative',
            flex: 1,
          }}
        >
          {sinAsignar.map(opl => (
            <SinAsignarOplChip
              key={opl.id_opl}
              opl={opl}
              isDragging={draggingOpl?.id_opl === opl.id_opl}
              onDragStart={e => {
                if (opl.tipo_asignacion === 'arrastre') { e.preventDefault(); return }
                e.dataTransfer.effectAllowed = 'move'
                e.dataTransfer.setData('text/plain', opl.id_opl)
                setTimeout(() => setDraggingOpl({
                  id_opl: opl.id_opl,
                  tiempo_planificado: opl.tiempo_planificado ?? 0,
                  tiempo_total_teorico: opl.tiempo_total_teorico ?? opl.tiempo_planificado ?? 0,
                }), 0)
              }}
              onDragEnd={handleDragEnd}
              readonly={readonly}
              matches={matchesQuery(opl, searchQuery)}
              searchQueryActive={trimmedQuery !== ''}
            />
          ))}
          {sinAsignar.length === 0 && !draggingOpl && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Arrastra aquí para desasignar
            </span>
          )}

          {draggingOpl && (
            <div
              onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setSinAsignarOver(true) }}
              onDragLeave={() => setSinAsignarOver(false)}
              onDrop={e => {
                e.preventDefault()
                setSinAsignarOver(false)
                const idOpl = e.dataTransfer.getData('text/plain')
                if (idOpl) onDrop(idOpl, null)
                handleDragEnd()
              }}
              style={{
                position: 'absolute', inset: 0,
                zIndex: 10,
                cursor: 'copy',
                background: sinAsignarOver ? 'rgba(156,163,175,0.15)' : 'transparent',
                transition: 'background 0.1s',
              }}
            />
          )}
        </div>
      </div>
    </div>

      {/* Modal Re-optimizar */}
      {showReoptimizeConfirm && createPortal(
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) setShowReoptimizeConfirm(false) }}>
          <div className="modal-box" style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <span className="modal-title">Confirmar re-optimización</span>
              <button className="modal-close" onClick={() => setShowReoptimizeConfirm(false)}>×</button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{
                display: 'flex', alignItems: 'flex-start', gap: 12,
                background: '#fffbeb', border: '1px solid #fcd34d',
                borderRadius: 8, padding: '12px 14px',
              }}>
                <span style={{ fontSize: 18, lineHeight: 1, flexShrink: 0, marginTop: 1 }}>⚠</span>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: '#92400e', marginBottom: 4 }}>
                    {nNoFijas} {nNoFijas !== 1 ? 'asignaciones' : 'asignación'} no fija{nNoFijas !== 1 ? 's' : ''} se perderá{nNoFijas !== 1 ? 'n' : ''}
                  </div>
                  <div style={{ fontSize: 12.5, color: '#78350f', lineHeight: 1.5 }}>
                    Las OPLs sin fijar volverán al estado sin asignar. Las bloqueadas con 🔒 se conservan.
                  </div>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-ghost" onClick={() => setShowReoptimizeConfirm(false)}>Cancelar</button>
              <button
                onClick={() => { setShowReoptimizeConfirm(false); onReoptimize() }}
                style={{
                  padding: '8px 16px',
                  background: 'var(--accent, #111827)', color: '#fff',
                  border: 'none', borderRadius: 6, fontSize: 14, cursor: 'pointer',
                }}
              >
                ↺ Re-optimizar
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Modal Limpiar selectivo */}
      {showLimpiarModal && createPortal(
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget && !limpiarLoading) setShowLimpiarModal(false) }}>
          <div className="modal-box">
            <div className="modal-header">
              <span className="modal-title">Limpiar reparto</span>
              <button className="modal-close" onClick={() => setShowLimpiarModal(false)} disabled={limpiarLoading}>×</button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {/* Opción: Desfijar */}
              <button
                onClick={() => setLimpiarDesfijar(v => !v)}
                disabled={limpiarLoading}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 12,
                  width: '100%', textAlign: 'left',
                  background: limpiarDesfijar ? '#eff6ff' : 'var(--surface)',
                  border: `1.5px solid ${limpiarDesfijar ? '#2563eb' : 'var(--border, #e5e7eb)'}`,
                  borderRadius: 8, padding: '12px 14px', cursor: limpiarLoading ? 'not-allowed' : 'pointer',
                  transition: 'border-color 0.15s, background 0.15s',
                }}
              >
                <div style={{
                  flexShrink: 0, width: 16, height: 16, borderRadius: 4,
                  border: `2px solid ${limpiarDesfijar ? '#2563eb' : 'var(--border, #e5e7eb)'}`,
                  background: limpiarDesfijar ? '#2563eb' : 'var(--surface)',
                  marginTop: 2, display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {limpiarDesfijar && <span style={{ color: '#fff', fontSize: 10, fontWeight: 700 }}>✓</span>}
                </div>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text)', marginBottom: 3 }}>
                    🔓 Desbloquear asignaciones fijadas
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.45 }}>
                    Las asignaciones bloqueadas manualmente vuelven a ser editables. No se borra nada.
                  </div>
                </div>
              </button>

              {/* Opción: Normalizar obligatorias */}
              <button
                onClick={() => setLimpiarNormalizar(v => !v)}
                disabled={limpiarLoading}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 12,
                  width: '100%', textAlign: 'left',
                  background: limpiarNormalizar ? '#fffbeb' : 'var(--surface)',
                  border: `1.5px solid ${limpiarNormalizar ? '#d97706' : 'var(--border, #e5e7eb)'}`,
                  borderRadius: 8, padding: '12px 14px', cursor: limpiarLoading ? 'not-allowed' : 'pointer',
                  transition: 'border-color 0.15s, background 0.15s',
                }}
              >
                <div style={{
                  flexShrink: 0, width: 16, height: 16, borderRadius: 4,
                  border: `2px solid ${limpiarNormalizar ? '#d97706' : 'var(--border, #e5e7eb)'}`,
                  background: limpiarNormalizar ? '#d97706' : 'var(--surface)',
                  marginTop: 2, display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {limpiarNormalizar && <span style={{ color: '#fff', fontSize: 10, fontWeight: 700 }}>✓</span>}
                </div>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text)', marginBottom: 3 }}>
                    ↓ Convertir obligatorias en normales
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.45 }}>
                    Las OPLs marcadas como obligatorias pasan a tratarse como normales. Se mantiene la asignación actual.
                  </div>
                </div>
              </button>

              {/* Opción: Eliminar arrastre */}
              <button
                onClick={() => setLimpiarArrastre(v => !v)}
                disabled={limpiarLoading}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 12,
                  width: '100%', textAlign: 'left',
                  background: limpiarArrastre ? '#fef2f2' : 'var(--surface)',
                  border: `1.5px solid ${limpiarArrastre ? '#dc2626' : 'var(--border, #e5e7eb)'}`,
                  borderRadius: 8, padding: '12px 14px', cursor: limpiarLoading ? 'not-allowed' : 'pointer',
                  transition: 'border-color 0.15s, background 0.15s',
                }}
              >
                <div style={{
                  flexShrink: 0, width: 16, height: 16, borderRadius: 4,
                  border: `2px solid ${limpiarArrastre ? '#dc2626' : 'var(--border, #e5e7eb)'}`,
                  background: limpiarArrastre ? '#dc2626' : 'var(--surface)',
                  marginTop: 2, display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {limpiarArrastre && <span style={{ color: '#fff', fontSize: 10, fontWeight: 700 }}>✓</span>}
                </div>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text)', marginBottom: 3 }}>
                    ✕ Eliminar arrastres
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.45 }}>
                    Borra las OPLs pendientes arrastradas de la semana anterior. Esta acción no se puede deshacer.
                  </div>
                </div>
              </button>
            </div>

            <div className="modal-footer">
              <button
                className="btn-ghost"
                onClick={() => setShowLimpiarModal(false)}
                disabled={limpiarLoading}
              >
                Cancelar
              </button>
              <button
                onClick={handleLimpiarConfirm}
                disabled={(!limpiarDesfijar && !limpiarNormalizar && !limpiarArrastre) || limpiarLoading}
                style={{
                  padding: '8px 16px',
                  background: 'var(--accent, #111827)', color: '#fff',
                  border: 'none', borderRadius: 6, fontSize: 14, cursor: 'pointer',
                  opacity: (!limpiarDesfijar && !limpiarNormalizar && !limpiarArrastre) || limpiarLoading ? 0.4 : 1,
                }}
              >
                {limpiarLoading ? 'Aplicando...' : 'Aplicar selección'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Dropdown sugerencias buscador */}
      {showSuggestions && (hasAnySection || trimmedQuery !== '') && createPortal(
        <div
          id="opl-search-suggestions"
          role="listbox"
          className="opl-search-pop"
          style={{
            position: 'fixed',
            top: dropdownPos.top,
            left: dropdownPos.left,
            width: Math.max(dropdownPos.width, 320),
            maxHeight: 'min(64vh, 520px)',
            background: 'rgba(255,255,255,0.92)',
            backdropFilter: 'blur(18px) saturate(160%)',
            WebkitBackdropFilter: 'blur(18px) saturate(160%)',
            border: '1px solid rgba(37,99,235,0.35)',
            borderRadius: 12,
            boxShadow: '0 14px 40px -8px rgba(15,23,42,0.22), 0 4px 12px -2px rgba(15,23,42,0.08), 0 0 0 1px rgba(37,99,235,0.04)',
            zIndex: 9999,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Cabecera con conteo de matches */}
          {trimmedQuery !== '' && (
            <div style={{
              padding: '8px 14px',
              fontSize: 10.5,
              color: 'var(--text-muted, #6b7280)',
              borderBottom: '1px solid rgba(229,231,235,0.7)',
              background: 'linear-gradient(180deg, rgba(239,246,255,0.6) 0%, rgba(239,246,255,0) 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
              flexShrink: 0,
            }}>
              <span style={{
                fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
                fontVariantNumeric: 'tabular-nums',
                color: matchCount === 0 ? '#b91c1c' : 'var(--text-muted)',
                fontWeight: 600,
              }}>
                {matchCount} en reparto
              </span>
            </div>
          )}

          {/* Contenedor scrolleable con todas las sugerencias */}
          <div
            className="opl-sug-scroll"
            style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}
          >

          {/* Sección OPLs */}
          {suggestOpls.length > 0 && (
            <div>
              <SectionHeader
                icon={<IconOpl />}
                label="OPL"
                count={suggestOpls.length}
                accent="#2563eb"
                collapsed={sectionCollapsed.opl}
                onToggle={() => { setSectionCollapsed(s => ({ ...s, opl: !s.opl })); setActiveIdx(0) }}
              />
              {!sectionCollapsed.opl && suggestOpls.map((id, i) => {
                const idx = i
                const active = idx === safeActiveIdx
                return (
                  <button
                    key={id}
                    id={`opl-sug-${idx}`}
                    role="option"
                    aria-selected={active}
                    data-active={active || undefined}
                    onMouseEnter={() => setActiveIdx(idx)}
                    onMouseDown={e => { e.preventDefault(); pickSuggestion(id) }}
                    className="opl-sug-row"
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      width: '100%', textAlign: 'left',
                      padding: '7px 14px', fontSize: 12.5,
                      background: active ? 'linear-gradient(90deg, rgba(37,99,235,0.10) 0%, rgba(37,99,235,0.04) 100%)' : 'transparent',
                      borderLeft: `2px solid ${active ? '#2563eb' : 'transparent'}`,
                      border: 'none', borderBottom: 'none',
                      cursor: 'pointer', color: 'var(--text, #111827)',
                      transition: 'background 0.1s, border-color 0.1s',
                    }}
                  >
                    <span style={{
                      fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
                      fontWeight: 600, color: '#1d4ed8',
                      letterSpacing: '-0.01em',
                    }}>
                      {highlight(id, trimmedQuery)}
                    </span>
                    {active && (
                      <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 3, color: '#6b7280', fontSize: 10 }}>
                        <span>ir</span>
                        <IconArrow size={9} />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Sección Artículos */}
          {suggestArticulos.length > 0 && (
            <div style={{ borderTop: suggestOpls.length > 0 ? '1px solid rgba(229,231,235,0.7)' : 'none' }}>
              <SectionHeader
                icon={<IconArticulo />}
                label="Artículo"
                count={suggestArticulos.length}
                accent="#0891b2"
                collapsed={sectionCollapsed.articulo}
                onToggle={() => { setSectionCollapsed(s => ({ ...s, articulo: !s.articulo })); setActiveIdx(0) }}
              />
              {!sectionCollapsed.articulo && suggestArticulos.map(([ref, nombre], i) => {
                const idx = (sectionCollapsed.opl ? 0 : suggestOpls.length) + i
                const active = idx === safeActiveIdx
                return (
                  <button
                    key={ref}
                    id={`opl-sug-${idx}`}
                    role="option"
                    aria-selected={active}
                    data-active={active || undefined}
                    onMouseEnter={() => setActiveIdx(idx)}
                    onMouseDown={e => { e.preventDefault(); pickSuggestion(ref) }}
                    className="opl-sug-row"
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      width: '100%', textAlign: 'left',
                      padding: '7px 14px', fontSize: 12.5,
                      background: active ? 'linear-gradient(90deg, rgba(8,145,178,0.10) 0%, rgba(8,145,178,0.04) 100%)' : 'transparent',
                      borderLeft: `2px solid ${active ? '#0891b2' : 'transparent'}`,
                      border: 'none',
                      cursor: 'pointer', color: 'var(--text, #111827)',
                      transition: 'background 0.1s, border-color 0.1s',
                      minWidth: 0,
                    }}
                  >
                    <span style={{ fontWeight: 600, color: '#0e7490', flexShrink: 0 }}>
                      {highlight(ref, trimmedQuery)}
                    </span>
                    {nombre && (
                      <span style={{
                        color: '#6b7280', fontSize: 11,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        minWidth: 0, flex: 1,
                      }}>
                        · {highlight(nombre, trimmedQuery)}
                      </span>
                    )}
                    {active && (
                      <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 3, color: '#6b7280', fontSize: 10, flexShrink: 0 }}>
                        <span>ir</span>
                        <IconArrow size={9} />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Sección Familias */}
          {suggestFamilias.length > 0 && (
            <div style={{ borderTop: (suggestOpls.length > 0 || suggestArticulos.length > 0) ? '1px solid rgba(229,231,235,0.7)' : 'none' }}>
              <SectionHeader
                icon={<IconFamilia />}
                label="Familia"
                count={suggestFamilias.length}
                accent="#7c3aed"
                collapsed={sectionCollapsed.familia}
                onToggle={() => { setSectionCollapsed(s => ({ ...s, familia: !s.familia })); setActiveIdx(0) }}
              />
              {!sectionCollapsed.familia && suggestFamilias.map((f, i) => {
                const idx = (sectionCollapsed.opl ? 0 : suggestOpls.length) + (sectionCollapsed.articulo ? 0 : suggestArticulos.length) + i
                const active = idx === safeActiveIdx
                return (
                  <button
                    key={f}
                    id={`opl-sug-${idx}`}
                    role="option"
                    aria-selected={active}
                    data-active={active || undefined}
                    onMouseEnter={() => setActiveIdx(idx)}
                    onMouseDown={e => { e.preventDefault(); pickSuggestion(f) }}
                    className="opl-sug-row"
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      width: '100%', textAlign: 'left',
                      padding: '7px 14px', fontSize: 12.5,
                      background: active ? 'linear-gradient(90deg, rgba(124,58,237,0.10) 0%, rgba(124,58,237,0.04) 100%)' : 'transparent',
                      borderLeft: `2px solid ${active ? '#7c3aed' : 'transparent'}`,
                      border: 'none',
                      cursor: 'pointer', color: 'var(--text, #111827)',
                      transition: 'background 0.1s, border-color 0.1s',
                    }}
                  >
                    <span style={{ fontWeight: 600, color: '#6d28d9' }}>{highlight(f, trimmedQuery)}</span>
                    {active && (
                      <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 3, color: '#6b7280', fontSize: 10 }}>
                        <span>ir</span>
                        <IconArrow size={9} />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Empty state */}
          {!hasSuggestions && trimmedQuery !== '' && (
            <div style={{
              padding: '20px 14px',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
              color: 'var(--text-muted, #6b7280)',
            }}>
              <div style={{
                width: 30, height: 30, borderRadius: '50%',
                background: 'rgba(220,38,38,0.08)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#dc2626',
              }}>
                <IconSearch size={14} />
              </div>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text, #111827)' }}>Sin sugerencias</div>
              <div style={{ fontSize: 11, textAlign: 'center', maxWidth: 240, lineHeight: 1.45 }}>
                Ningún OPL, artículo o familia coincide con «<span style={{ fontFamily: 'ui-monospace, monospace', color: '#dc2626' }}>{trimmedQuery}</span>».
              </div>
            </div>
          )}

          </div>
        </div>,
        document.body
      )}

      {/* Modal Añadir OPLs sin reparto */}
      {showAddOplsModal && createPortal(
        <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget && !addOplsSubmitting) setShowAddOplsModal(false) }}>
          <div className="modal-box" style={{ width: 680 }}>
            <div className="modal-header">
              <span className="modal-title">Añadir OPLs a sin asignar</span>
              <button className="modal-close" onClick={() => setShowAddOplsModal(false)} disabled={addOplsSubmitting}>×</button>
            </div>
            <div style={{ padding: '10px 24px 6px', fontSize: 13, color: 'var(--text-muted)', flexShrink: 0 }}>
              Selecciona OPLs para incluir en este reparto sin asignar operario.
              Al reoptimizar aparecerán como normales.
            </div>
            <div style={{ flex: 1, overflow: 'auto', minHeight: 0, padding: '0 24px 8px', pointerEvents: addOplsSubmitting ? 'none' : 'auto', opacity: addOplsSubmitting ? 0.5 : 1 }}>
              <TablaSeleccionOpl
                opls={oplsSinReparto}
                selectedIds={addOplsSelected}
                obligatoriaIds={[]}
                articulosByRef={articulosByRef}
                onChange={setAddOplsSelected}
              />
            </div>
            <div className="modal-footer">
              <button className="btn-ghost" onClick={() => setShowAddOplsModal(false)} disabled={addOplsSubmitting}>
                Cancelar
              </button>
              <button
                disabled={addOplsSelected.length === 0 || addOplsSubmitting}
                onClick={async () => {
                  setAddOplsSubmitting(true)
                  try {
                    await onAddOpls(addOplsSelected)
                    setShowAddOplsModal(false)
                    setAddOplsSelected([])
                  } finally {
                    setAddOplsSubmitting(false)
                  }
                }}
                style={{
                  padding: '8px 16px',
                  background: 'var(--accent, #111827)', color: '#fff',
                  border: 'none', borderRadius: 6, fontSize: 14, cursor: 'pointer',
                  opacity: addOplsSelected.length === 0 || addOplsSubmitting ? 0.4 : 1,
                }}
              >
                {addOplsSubmitting
                  ? 'Añadiendo…'
                  : `Añadir ${addOplsSelected.length} OPL${addOplsSelected.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  )
}
