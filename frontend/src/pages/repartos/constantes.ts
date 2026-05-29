export const PAGE_SIZE = 50

export type PerfilKey = 'produccion' | 'balanceado' | 'personas'

export const PERFILES = [
  {
    key: 'produccion' as PerfilKey, title: 'Producción',
    desc: 'Los mejores operarios para cada OPL, aunque la carga sea menos equitativa',
  },
  {
    key: 'balanceado' as PerfilKey, title: 'Balanceado',
    desc: 'Buen equilibrio entre asignar operarios cualificados y repartir carga',
  },
  {
    key: 'personas' as PerfilKey, title: 'Personas',
    desc: 'Prioriza que todos los operarios tengan una carga similar',
  },
] as const

export type FaseKey = 'eficiencia' | 'equidad_peso' | 'equidad_articulos'

export const MODO_FASES_ACTIVAS: Record<PerfilKey, { eficiencia: boolean; equidad_peso: boolean; equidad_articulos: boolean }> = {
  produccion: { eficiencia: true,  equidad_peso: false, equidad_articulos: false },
  balanceado: { eficiencia: true,  equidad_peso: true,  equidad_articulos: false },
  personas:   { eficiencia: true,  equidad_peso: true,  equidad_articulos: true },
}

export const TIEMPO_MIN = 1
export const TIEMPO_MAX = 15
export const TIEMPO_DEFAULT = 5
export const TIEMPO_MARKS = [1, 5, 10, 15] as const

// ── Tiempo MÍNIMO sugerido por modo ──────────────────────────────────────
// Calibrado por benchmark: con 2 min producción ya da grado de satisfacción
// alto (solo fase eficiencia); balanceado y personas necesitan 3 min para
// que las fases de equidad devuelvan un resultado aplicable.
export const TIEMPO_MINIMO_POR_MODO: Record<PerfilKey, number> = {
  produccion: 2,
  balanceado: 3,
  personas:   3,
}

export type StepKey = 'opls' | 'config' | 'ejecucion'

export const STEPS = [
  { key: 'opls' as StepKey,      label: 'OPLs',          number: 1 },
  { key: 'config' as StepKey,    label: 'Configuración', number: 2 },
  { key: 'ejecucion' as StepKey, label: 'Ejecución',     number: 3 },
] as const

export type FaseProgresoKey = 'base' | FaseKey

export const FASES_PROGRESO = [
  { key: 'base' as FaseProgresoKey,               label: 'Base',                desc: 'Maximiza minutos asignados' },
  { key: 'eficiencia' as FaseProgresoKey,         label: 'Eficiencia',          desc: 'Asigna operarios cualificados' },
  { key: 'equidad_peso' as FaseProgresoKey,       label: 'Equidad de peso',     desc: 'Equilibra kg entre operarios' },
  { key: 'equidad_articulos' as FaseProgresoKey,  label: 'Equidad de artículos', desc: 'Equilibra artículos entre operarios' },
] as const
