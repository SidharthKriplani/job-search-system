/**
 * Detect seniority from résumé text — shown explicitly on upload and stored so
 * the feed ranks jobs to the user's rung. Mirror of the rank logic in
 * utils/role_graph.py (LEVEL_RANK + user_level).
 */

export type Level = 'entry' | 'mid' | 'senior' | 'lead' | 'director'

const LEVEL_ORDER: Level[] = ['entry', 'mid', 'senior', 'lead', 'director']
const RANK: Record<Level, number> = { entry: 1, mid: 2, senior: 3, lead: 4, director: 5 }

const LABEL: Record<Level, string> = {
  entry: 'Entry / Analyst',
  mid: 'Mid / Associate',
  senior: 'Senior',
  lead: 'Lead / VP',
  director: 'Director+',
}

// Highest title cue present in the résumé → level. Checked high→low.
const TITLE_CUES: [Level, string[]][] = [
  ['director', ['managing director', ' md ', 'chief ', ' cxo', 'head of', 'partner', 'executive director', ' ed ', 'director']],
  ['lead', ['vice president', ' vp ', ' avp', ' svp', 'principal', ' staff ', 'team lead', ' lead ', 'manager']],
  ['senior', ['senior', ' sr ', ' sr.']],
  ['mid', ['associate']],
  ['entry', ['analyst', 'junior', ' jr ', 'graduate', 'trainee', 'intern', 'fresher']],
]

function levelFromYears(years: number | null): Level | null {
  if (years == null) return null
  if (years <= 1) return 'entry'
  if (years <= 4) return 'mid'
  if (years <= 8) return 'senior'
  if (years <= 12) return 'lead'
  return 'director'
}

export function seniorityFromText(text: string): { years: number | null; level: Level | null; label: string } {
  const low = ` ${(text || '').toLowerCase().replace(/\s+/g, ' ')} `

  // Years: take the largest "<n> years" / "<n>+ years" mention.
  let years: number | null = null
  for (const m of low.matchAll(/(\d{1,2})\s*\+?\s*years?/g)) {
    const n = parseInt(m[1], 10)
    if (!isNaN(n) && (years == null || n > years)) years = n
  }

  // Title cue: highest rung present.
  let titleLevel: Level | null = null
  for (const [lvl, cues] of TITLE_CUES) {
    if (cues.some(c => low.includes(c))) { titleLevel = lvl; break }
  }

  const yearLevel = levelFromYears(years)
  // Take the more senior of the two signals.
  let level: Level | null = null
  for (const cand of [titleLevel, yearLevel]) {
    if (cand && (!level || RANK[cand] > RANK[level])) level = cand
  }

  const label = level
    ? `${LABEL[level]}${years != null ? ` · ~${years} yrs` : ''}`
    : (years != null ? `~${years} yrs` : '')
  return { years, level, label }
}
