/**
 * Convierte un `Date` a string ISO `YYYY-MM-DD` en hora local (sin desfase UTC).
 * @param date Fecha a formatear.
 * @returns La fecha en formato ISO `YYYY-MM-DD`.
 */
export function toISODate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Parsea una fecha ISO `YYYY-MM-DD` a `Date` en hora local (evita el parse UTC nativo).
 * @param isoDate Fecha en formato `YYYY-MM-DD`.
 * @returns El `Date` correspondiente a medianoche local.
 */
export function parseISODate(isoDate: string): Date {
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1)
}

/**
 * Devuelve el lunes de la semana a la que pertenece una fecha.
 * @param date Fecha cualquiera de la semana.
 * @returns Un `Date` apuntando al lunes (semana ISO, lunes-domingo).
 */
export function getMondayFromDate(date: Date): Date {
  const normalized = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const day = normalized.getDay()
  const offset = day === 0 ? -6 : 1 - day
  normalized.setDate(normalized.getDate() + offset)
  return normalized
}

/**
 * Lunes de la semana actual en formato ISO.
 * @returns El lunes de esta semana como `YYYY-MM-DD`.
 */
export function getTodayMondayISO(): string {
  return toISODate(getMondayFromDate(new Date()))
}

/**
 * Suma (o resta, con valores negativos) días a una fecha ISO.
 * @param isoDate Fecha base en `YYYY-MM-DD`.
 * @param days Número de días a sumar.
 * @returns La fecha resultante en `YYYY-MM-DD`.
 */
export function addDaysToISO(isoDate: string, days: number): string {
  const date = parseISODate(isoDate)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

/** Una semana del calendario: su lunes y los siete días que la componen. */
export interface WeekInfo {
  monday: Date
  days: Date[]
}

/**
 * Genera las semanas (lunes-domingo) que cubren un mes para pintar el calendario.
 *
 * Devuelve hasta 6 semanas, recortando las semanas finales que ya no tocan el mes.
 * @param year Año.
 * @param month Mes en base 0 (0 = enero).
 * @returns Lista de semanas con su lunes y sus días.
 */
export function getWeeksForMonth(year: number, month: number): WeekInfo[] {
  const firstOfMonth = new Date(year, month, 1)
  const monday = getMondayFromDate(firstOfMonth)

  const weeks: WeekInfo[] = []
  while (weeks.length < 6) {
    const days: Date[] = []
    for (let i = 0; i < 7; i++) {
      const day = new Date(monday)
      day.setDate(day.getDate() + i)
      days.push(day)
    }

    if (weeks.length >= 4 && days[0]!.getMonth() !== month) break
    weeks.push({ monday: new Date(monday), days })
    monday.setDate(monday.getDate() + 7)
  }

  return weeks
}

/**
 * Calcula el número de semana ISO 8601 de una fecha.
 * @param dateValue Fecha a evaluar.
 * @returns El número de semana ISO (1-53).
 */
export function getISOWeek(dateValue: Date): number {
  const date = new Date(Date.UTC(dateValue.getFullYear(), dateValue.getMonth(), dateValue.getDate()))
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7))
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1))
  return Math.ceil(((+date - +yearStart) / 86400000 + 1) / 7)
}

/**
 * Etiqueta legible de una semana, p. ej. `"Semana 23 · 2026"`.
 * @param isoDate Lunes de la semana en `YYYY-MM-DD`.
 * @returns Texto con número de semana ISO y año.
 */
export function formatSemanaLabel(isoDate: string): string {
  const date = parseISODate(isoDate)
  return `Semana ${getISOWeek(date)} · ${date.getFullYear()}`
}

/** Formato España: dd-mm-aaaa */
export function formatFechaES(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  if (!year || !month || !day) return isoDate
  return `${day}-${month}-${year}`
}
