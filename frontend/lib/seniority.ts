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
  const full = ` ${(text || '').toLowerCase().replace(/\s+/g, ' ')} `
  // Title/level cues only from the HEADER region (top ~500 chars) — that's where
  // the candidate's own current title lives. Scanning the whole doc fires on
  // "reported to the MD", "senior stakeholders", etc. and inflates the level.
  const head = full.slice(0, 520)

  // Years: prefer an explicit experience phrase ("8+ years of experience",
  // "7 years in investment banking"). Only fall back to a bare "N years" if no
  // experience phrase exists — and cap it, since résumé prose is full of stray
  // durations ("over 3 years", "10-year initiative").
  let years: number | null = null
  for (const m of full.matchAll(/(\d{1,2})\s*\+?\s*years?(?:\s+of)?\s+(?:experience|exp\b|in\s)/g)) {
    const n = parseInt(m[1], 10)
    if (!isNaN(n) && (years == null || n > years)) years = n
  }
  if (years == null) {
    // No clear experience phrase — take the largest bare "N years" but cap at 10
    // so a stray big number can't push someone to director.
    for (const m of head.matchAll(/(\d{1,2})\s*\+?\s*years?/g)) {
      const n = Math.min(parseInt(m[1], 10), 10)
      if (!isNaN(n) && (years == null || n > years)) years = n
    }
  }

  let titleLevel: Level | null = null
  for (const [lvl, cues] of TITLE_CUES) {
    if (cues.some(c => head.includes(c))) { titleLevel = lvl; break }
  }

  const yearLevel = levelFromYears(years)
  // Reconcile: if the title cue and the years disagree by MORE than one rung,
  // trust the years (a single stray title word shouldn't override). Otherwise
  // take the more senior of the two.
  let level: Level | null = titleLevel
  if (titleLevel && yearLevel) {
    if (Math.abs(RANK[titleLevel] - RANK[yearLevel]) > 1) level = yearLevel
    else level = RANK[titleLevel] >= RANK[yearLevel] ? titleLevel : yearLevel
  } else {
    level = titleLevel || yearLevel
  }

  const label = level
    ? `${LABEL[level]}${years != null ? ` · ~${years} yrs` : ''}`
    : (years != null ? `~${years} yrs` : '')
  return { years, level, label }
}
