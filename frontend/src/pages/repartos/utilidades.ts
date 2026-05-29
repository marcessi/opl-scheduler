export function estadoBadgeClass(estado: string | null | undefined): string {
  if (!estado) return 'fase-badge fase-other'
  const s = estado.toUpperCase()
  if (s === 'OPTIMA' || s === 'OPTIMAL') return 'fase-badge fase-optima'
  if (s === 'FACTIBLE' || s === 'FEASIBLE') return 'fase-badge fase-factible'
  if (s === 'INFACTIBLE' || s === 'INFEASIBLE') return 'fase-badge fase-infactible'
  return 'fase-badge fase-other'
}

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

export function getTiempoLabel(min: number): string {
  return `~${min} min`
}
