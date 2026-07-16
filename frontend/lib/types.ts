export type ApplicationStage =
  | 'Not Applied'
  | 'Applied'
  | 'Application Acknowledged'
  | 'Recruiter Screening'
  | 'HM Interview Scheduled'
  | 'HM Interview Done'
  | 'Technical Round Scheduled'
  | 'Technical Round Done'
  | 'Case Study / Assignment'
  | 'Final Round Scheduled'
  | 'Final Round Done'
  | 'Reference Check'
  | 'Background Check'
  | 'Offer Verbal'
  | 'Offer Written'
  | 'Offer Negotiating'
  | 'Offer Accepted'
  | 'Rejected'
  | 'Withdrawn'
  | 'Ghosted'

export interface UserProfile {
  id: string
  user_id: string
  full_name: string | null
  email: string | null
  target_roles: string[]
  salary_floor: number
  locations: string[]
  experience_years: number
  industries: string[]
  target_companies: string[]
  exclude_companies: string[]
  is_active: boolean
  gmail_connected: boolean
  resume_text: string | null
  seniority_level: string | null
  created_at: string
  updated_at: string
}

export interface Job {
  id: string
  user_id: string
  job_title: string
  company: string
  location: string | null
  salary_range: string | null
  job_url: string
  description_snippet: string | null
  posted_date: string | null
  source: string
  source_job_id: string
  job_type: string
  seniority: string | null
  is_new: boolean
  is_applied: boolean
  is_saved: boolean
  is_dismissed: boolean
  match_score: number
  match_reasons: string[]
  scraped_at: string
}

export interface Application {
  id: string
  user_id: string
  job_feed_id: string | null
  company: string
  job_title: string
  job_url: string | null
  location: string | null
  salary_offered: string | null
  stage: ApplicationStage
  date_applied: string | null
  date_stage_updated: string | null
  follow_up_date: string | null
  next_action: string | null
  recruiter_name: string | null
  recruiter_email: string | null
  recruiter_linkedin: string | null
  hiring_manager_name: string | null
  referral_contact: string | null
  notes: string | null
  prep_notes: string | null
  rejection_reason: string | null
  source: string | null
  priority: 'high' | 'medium' | 'low'
  created_at: string
  updated_at: string
}

export interface ReferralContact {
  id: string
  user_id: string
  company: string
  contact_name: string
  contact_role: string | null
  contact_linkedin: string | null
  contact_email: string | null
  status: 'identified' | 'message_drafted' | 'message_sent' | 'responded' | 'call_scheduled' | 'referred' | 'not_responding' | 'declined'
  message_sent_date: string | null
  response_date: string | null
  follow_up_date: string | null
  notes: string | null
  connection_type: string | null
  created_at: string
}

export interface ScraperHealth {
  source: string
  last_run_at: string | null
  last_success_at: string | null
  last_job_count: number
  consecutive_failures: number
  last_error: string | null
  status: 'ok' | 'warning' | 'error'
}

export const STAGE_COLORS: Record<ApplicationStage, string> = {
  'Not Applied':              'bg-slate-100 text-slate-600',
  'Applied':                  'bg-blue-100 text-blue-700',
  'Application Acknowledged': 'bg-blue-100 text-blue-700',
  'Recruiter Screening':      'bg-violet-100 text-violet-700',
  'HM Interview Scheduled':   'bg-violet-100 text-violet-700',
  'HM Interview Done':        'bg-purple-100 text-purple-700',
  'Technical Round Scheduled':'bg-purple-100 text-purple-700',
  'Technical Round Done':     'bg-purple-100 text-purple-700',
  'Case Study / Assignment':  'bg-orange-100 text-orange-700',
  'Final Round Scheduled':    'bg-orange-100 text-orange-700',
  'Final Round Done':         'bg-orange-100 text-orange-700',
  'Reference Check':          'bg-yellow-100 text-yellow-700',
  'Background Check':         'bg-yellow-100 text-yellow-700',
  'Offer Verbal':             'bg-emerald-100 text-emerald-700',
  'Offer Written':            'bg-emerald-100 text-emerald-700',
  'Offer Negotiating':        'bg-emerald-100 text-emerald-700',
  'Offer Accepted':           'bg-green-100 text-green-700',
  'Rejected':                 'bg-red-100 text-red-600',
  'Withdrawn':                'bg-slate-100 text-slate-500',
  'Ghosted':                  'bg-slate-100 text-slate-500',
}

export const SOURCE_LABELS: Record<string, string> = {
  workday:          'Workday',
  oracle:           'Oracle',
  smartrecruiters:  'SmartRecruiters',
  greenhouse:       'Greenhouse',
  lever:            'Lever',
  iimjobs:          'iimjobs',
  foundit:          'Foundit',
  naukrigulf:       'NaukriGulf',
  bayt:             'Bayt',
  gulftalent:       'GulfTalent',
  instahyre:        'Instahyre',
  cutshort:         'Cutshort',
  ambitionbox:      'AmbitionBox',
  shine:            'Shine',
  timesjobs:        'TimesJobs',
  gmail_naukri:     '📧 Naukri Alert',
  gmail_linkedin:   '📧 LinkedIn Alert',
  gmail_iimjobs:    '📧 iimjobs Alert',
  gmail_indeed:     '📧 Indeed Alert',
  gmail_naukrigulf: '📧 NaukriGulf Alert',
  gmail_foundit:    '📧 Foundit Alert',
  gmail_timesjobs:  '📧 TimesJobs Alert',
  gmail_shine:      '📧 Shine Alert',
  // ATS + aggregators (ingestion engine)
  ashby:            'Ashby',
  indeed:           'Indeed',
  naukri:           'Naukri',
  linkedin:         'LinkedIn',
  glassdoor:        'Glassdoor',
  google:           'Google Jobs',
  remotive:         'Remotive',
  arbeitnow:        'Arbeitnow',
  adzuna_in:        'Adzuna India',
  adzuna_gb:        'Adzuna UK',
  adzuna_us:        'Adzuna US',
  // Source expansion (2026-07-15)
  workable:         'Workable',
  bamboohr:         'BambooHR',
  phenom:           'Phenom',
  eightfold:        'Eightfold',
  recruitee:        'Recruitee',
  jooble:           'Jooble',
}
