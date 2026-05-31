/**
 * Mapea un estado del solver a la clase CSS del badge que lo representa.
 * @param estado Estado de fase (OPTIMA, FACTIBLE, INFACTIBLE, ...).
 * @returns Clases CSS para el badge correspondiente.
 */
export function estadoBadgeClass(estado: string | null | undefined): string {
  if (!estado) return 'fase-badge fase-other'
  const s = estado.toUpperCase()
  if (s === 'OPTIMA' || s === 'OPTIMAL') return 'fase-badge fase-optima'
  if (s === 'FACTIBLE' || s === 'FEASIBLE') return 'fase-badge fase-factible'
  if (s === 'INFACTIBLE' || s === 'INFEASIBLE') return 'fase-badge fase-infactible'
  return 'fase-badge fase-other'
}

/**
 * Traduce un estado del solver a su etiqueta legible en español.
 * @param estado Estado de fase (acepta variantes en inglés del solver).
 * @returns Texto legible (`"Óptima"`, `"Ejecutando..."`, ...); `"—"` si es nulo.
 */
export function estadoLabel(estado: string | null | undefined): string {
  if (!estado) return '—'
  const s = estado.toUpperCase()
  if (s === 'OPTIMA' || s === 'OPTIMAL') return 'Óptima'
  if (s === 'FACTIBLE' || s === 'FEASIBLE') return 'Factible'
  if (s === 'INFACTIBLE' || s === 'INFEASIBLE') return 'Infactible'
  if (s === 'EJECUTANDO') return 'Ejecutando...'
  if (s === 'PENDIENTE') return 'Pendiente'
  if (s === 'NO_EJECUTADA') return 'Desactivada'
  return estado
}

/**
 * Formatea unos minutos como etiqueta aproximada de tiempo.
 * @param min Minutos.
 * @returns Texto del tipo `"~5 min"`.
 */
export function getTiempoLabel(min: number): string {
  return `~${min} min`
}
