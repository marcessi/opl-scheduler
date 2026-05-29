export function toISODate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function parseISODate(isoDate: string): Date {
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1)
}

export function getMondayFromDate(date: Date): Date {
  const normalized = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const day = normalized.getDay()
  const offset = day === 0 ? -6 : 1 - day
  normalized.setDate(normalized.getDate() + offset)
  return normalized
}

export function getTodayMondayISO(): string {
  return toISODate(getMondayFromDate(new Date()))
}

export function addDaysToISO(isoDate: string, days: number): string {
  const date = parseISODate(isoDate)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

export interface WeekInfo {
  monday: Date
  days: Date[]
}

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

export function getISOWeek(dateValue: Date): number {
  const date = new Date(Date.UTC(dateValue.getFullYear(), dateValue.getMonth(), dateValue.getDate()))
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7))
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1))
  return Math.ceil(((+date - +yearStart) / 86400000 + 1) / 7)
}

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
