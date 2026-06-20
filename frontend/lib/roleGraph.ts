/**
 * Read-guard mirror of utils/role_graph.py (KEEP ROUGHLY IN SYNC).
 *
 * The backend does the full weighted scoring; this file only needs the flat
 * keyword EXPANSION so the feed read-guard doesn't exclude adjacent roles. e.g.
 * for "data scientist" the guard must also let "Machine Learning Engineer"
 * through, which shares no word with the typed role. We collect each target
 * role's family members + sector keywords (minus over-generic words) and OR-match
 * them against title/description/company.
 */

const FAMILIES: Record<string, string[]> = {
  data_ml: [
    'data scientist', 'machine learning engineer', 'ai engineer', 'data engineer',
    'data analyst', 'analytics engineer', 'applied scientist', 'research scientist',
    'decision scientist', 'mlops engineer', 'business intelligence analyst',
    'product analyst', 'business analyst', 'data science manager', 'nlp engineer',
    'computer vision engineer', 'recommendation systems engineer',
  ],
  software: [
    'software engineer', 'backend engineer', 'frontend engineer', 'full stack engineer',
    'devops engineer', 'site reliability engineer', 'platform engineer', 'mobile engineer',
    'cloud engineer', 'security engineer', 'qa engineer',
  ],
  product: [
    'product manager', 'product owner', 'program manager', 'technical program manager',
    'product analyst', 'associate product manager', 'group product manager',
  ],
  design: [
    'product designer', 'ux designer', 'ui designer', 'ux researcher',
    'interaction designer', 'visual designer', 'design lead',
  ],
  finance_ib: [
    'investment banker', 'investment banking analyst', 'investment banking associate',
    'mergers and acquisitions', 'private equity associate', 'venture capital analyst',
    'equity research analyst', 'credit analyst', 'corporate development',
    'leveraged finance', 'capital markets', 'debt capital markets',
    'equity capital markets', 'restructuring', 'valuations analyst', 'financial analyst',
    'fp&a analyst', 'asset management', 'portfolio manager', 'hedge fund analyst',
    'quantitative analyst', 'risk analyst', 'transaction advisory', 'private credit',
    'treasury analyst', 'investment associate', 'fund manager',
  ],
  marketing: [
    'marketing manager', 'growth manager', 'performance marketing', 'digital marketing',
    'content marketing', 'brand manager', 'product marketing manager', 'seo specialist',
  ],
  sales: [
    'sales manager', 'account executive', 'business development manager', 'account manager',
    'sales development representative', 'inside sales', 'key account manager',
  ],
  consulting: [
    'management consultant', 'strategy consultant', 'business consultant',
    'associate consultant', 'strategy analyst', 'business analyst',
  ],
}

const FAMILY_SECTOR: Record<string, string | null> = {
  data_ml: null, software: null, product: null, design: null,
  finance_ib: 'finance', marketing: null, sales: null, consulting: null,
}

const SECTORS: Record<string, string[]> = {
  finance: [
    'finance', 'financial', 'bank', 'banking', 'capital', 'equity', 'securities',
    'investment', 'fund', 'wealth', 'hedge', 'private equity', 'venture capital',
    'merger', 'credit', 'lending', 'mortgage', 'treasury', 'brokerage', 'trading',
    'underwriting', 'valuation', 'portfolio', 'fintech', 'payments', 'insurance',
  ],
  fintech: ['fintech', 'payments', 'neobank', 'lending', 'wallet', 'remittance', 'kyc'],
  healthcare: ['healthcare', 'hospital', 'clinical', 'pharma', 'medical', 'biotech', 'healthtech'],
  ecommerce: ['ecommerce', 'e-commerce', 'retail', 'marketplace', 'd2c', 'logistics'],
}

const ALIASES: Record<string, string> = {
  'data science': 'data scientist', ds: 'data scientist',
  ml: 'machine learning engineer', 'ml engineer': 'machine learning engineer',
  'machine learning': 'machine learning engineer', ai: 'ai engineer', mle: 'machine learning engineer',
  ba: 'business analyst', bi: 'business intelligence analyst',
  swe: 'software engineer', sde: 'software engineer', sre: 'site reliability engineer',
  pm: 'product manager', apm: 'associate product manager', tpm: 'technical program manager',
  ux: 'ux designer', ui: 'ui designer',
  ib: 'investment banker', 'investment banking': 'investment banker',
  'm&a': 'mergers and acquisitions', pe: 'private equity associate', vc: 'venture capital analyst',
  er: 'equity research analyst', 'equity research': 'equity research analyst',
  quant: 'quantitative analyst',
}

const GENERIC = new Set([
  'engineer', 'manager', 'analyst', 'developer', 'lead', 'senior', 'junior', 'associate',
  'specialist', 'consultant', 'officer', 'executive', 'head', 'staff', 'principal',
  'director', 'intern', 'trainee', 'expert', 'professional', 'technician', 'support',
  'and', 'the', 'of',
])

const MEMBER_TO_FAMILY: Record<string, string> = {}
for (const [fam, members] of Object.entries(FAMILIES)) {
  for (const m of members) if (!(m in MEMBER_TO_FAMILY)) MEMBER_TO_FAMILY[m] = fam
}

function normalize(role: string): string {
  const r = (role || '').trim().toLowerCase()
  return ALIASES[r] || r
}

/** Distinctive keywords (>=3 chars, non-generic) that should let a job through. */
export function expandRoleKeywords(
  roles: string[] | null | undefined,
  industries?: string[] | null,
): string[] {
  const words = new Set<string>()
  const sectors = new Set<string>()

  const addPhrase = (phrase: string) => {
    for (const w of phrase.split(/\s+/)) {
      const c = w.replace(/[^a-z0-9&]/g, '')
      if (c.length >= 3 && !GENERIC.has(c)) words.add(c)
    }
  }

  for (const raw of roles || []) {
    const canon = normalize(raw)
    addPhrase(canon)
    const fam = MEMBER_TO_FAMILY[canon]
    if (fam) {
      for (const m of FAMILIES[fam]) addPhrase(m)
      if (FAMILY_SECTOR[fam]) sectors.add(FAMILY_SECTOR[fam] as string)
    }
  }
  for (const ind of industries || []) {
    const key = (ind || '').trim().toLowerCase()
    if (SECTORS[key]) sectors.add(key)
    else if (key.includes('fin') || key.includes('bank') || key.includes('invest')) sectors.add('finance')
    else if (key.includes('fintech')) sectors.add('fintech')
    else if (key.includes('health') || key.includes('pharma')) sectors.add('healthcare')
    else if (key.includes('commerce') || key.includes('retail')) sectors.add('ecommerce')
  }
  for (const s of sectors) for (const kw of SECTORS[s] || []) words.add(kw)

  return Array.from(words)
}
