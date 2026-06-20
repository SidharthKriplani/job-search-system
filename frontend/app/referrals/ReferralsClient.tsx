'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import { ReferralContact } from '@/lib/types'
import { createClient } from '@/lib/supabase'
import { Plus, Linkedin, Mail, X, Copy, Check, Upload, Sparkles } from 'lucide-react'
import clsx from 'clsx'

// ── LinkedIn Connections.csv helpers ─────────────────────────────────────────
// Normalise a company name for fuzzy matching (drop legal suffixes + punctuation).
const _COMPANY_NOISE = new Set([
  'inc', 'llc', 'ltd', 'limited', 'pvt', 'private', 'corp', 'corporation', 'co',
  'company', 'group', 'technologies', 'technology', 'tech', 'labs', 'lab',
  'solutions', 'services', 'systems', 'software', 'global', 'india', 'the',
])
function normCompany(s: string): string {
  return (s || '')
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, ' ')
    .split(/\s+/)
    .filter(w => w && !_COMPANY_NOISE.has(w))
    .join(' ')
    .trim()
}
function companiesMatch(a: string, b: string): boolean {
  const x = normCompany(a), y = normCompany(b)
  if (!x || !y) return false
  if (x === y) return true
  if (x.length >= 4 && y.length >= 4 && (x.includes(y) || y.includes(x))) return true
  return false
}

// Parse one CSV line, honouring double-quoted fields.
function parseCsvLine(line: string): string[] {
  const out: string[] = []
  let cur = '', inQ = false
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (inQ) {
      if (c === '"' && line[i + 1] === '"') { cur += '"'; i++ }
      else if (c === '"') inQ = false
      else cur += c
    } else {
      if (c === '"') inQ = true
      else if (c === ',') { out.push(cur); cur = '' }
      else cur += c
    }
  }
  out.push(cur)
  return out.map(s => s.trim())
}

interface ParsedConnection {
  contact_name: string
  company: string
  contact_role: string
  contact_linkedin: string
  contact_email: string
}

// LinkedIn's export has a few "Notes:" preamble lines before the real header
// (First Name,Last Name,URL,Email Address,Company,Position,Connected On).
function parseConnectionsCsv(text: string): ParsedConnection[] {
  const lines = text.split(/\r?\n/)
  const headerIdx = lines.findIndex(l => /first name/i.test(l) && /last name/i.test(l))
  if (headerIdx === -1) return []
  const header = parseCsvLine(lines[headerIdx]).map(h => h.toLowerCase())
  const col = (name: string) => header.findIndex(h => h.includes(name))
  const iFirst = col('first name'), iLast = col('last name'), iUrl = col('url')
  const iEmail = col('email'), iCompany = col('company'), iPos = col('position')

  const rows: ParsedConnection[] = []
  for (let i = headerIdx + 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue
    const f = parseCsvLine(lines[i])
    const name = [f[iFirst], f[iLast]].filter(Boolean).join(' ').trim()
    const company = (iCompany >= 0 ? f[iCompany] : '') || ''
    if (!name || !company) continue
    rows.push({
      contact_name:     name,
      company:          company.trim(),
      contact_role:     (iPos >= 0 ? f[iPos] : '') || '',
      contact_linkedin: (iUrl >= 0 ? f[iUrl] : '') || '',
      contact_email:    (iEmail >= 0 ? f[iEmail] : '') || '',
    })
  }
  return rows
}

const STATUS_COLORS: Record<string, string> = {
  identified:      'bg-slate-100 text-slate-600',
  message_drafted: 'bg-blue-100 text-blue-700',
  message_sent:    'bg-violet-100 text-violet-700',
  responded:       'bg-amber-100 text-amber-700',
  call_scheduled:  'bg-orange-100 text-orange-700',
  referred:        'bg-green-100 text-green-700',
  not_responding:  'bg-red-50 text-red-600',
  declined:        'bg-slate-100 text-slate-400',
}

const STATUS_LABELS: Record<string, string> = {
  identified:      'Identified',
  message_drafted: 'Draft Ready',
  message_sent:    'Sent',
  responded:       'Responded',
  call_scheduled:  'Call Scheduled',
  referred:        'Referred ✓',
  not_responding:  'No Response',
  declined:        'Declined',
}

interface Props {
  initialReferrals: ReferralContact[]
  templates: any[]
  userId: string
  feedCompanies: string[]
}

export default function ReferralsClient({ initialReferrals, templates, userId, feedCompanies }: Props) {
  const supabase = createClient()
  const [referrals, setReferrals] = useState(initialReferrals)
  const [showModal, setShowModal] = useState(false)
  const [newContact, setNewContact] = useState<Partial<ReferralContact>>({ status: 'identified' })
  const [saving, setSaving] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // ── LinkedIn import state ──
  const [showImport, setShowImport] = useState(false)
  const [parsed, setParsed] = useState<ParsedConnection[] | null>(null)
  const [matchesOnly, setMatchesOnly] = useState(true)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)

  // Which parsed connections are at a company in the user's feed/tracker.
  const matchIndex = (conn: ParsedConnection) =>
    feedCompanies.some(fc => companiesMatch(fc, conn.company))

  const visibleConns = (parsed || [])
    .map((c, i) => ({ c, i, match: matchIndex(c) }))
    .filter(x => (matchesOnly ? x.match : true))

  const matchCount = (parsed || []).filter(matchIndex).length

  const onFile = async (file: File) => {
    setImportError(null)
    setParsed(null)
    try {
      const text = await file.text()
      const rows = parseConnectionsCsv(text)
      if (rows.length === 0) {
        setImportError('Could not read that file. Make sure it is the Connections.csv from LinkedIn (unzipped).')
        return
      }
      setParsed(rows)
      // Pre-select everyone at a matching company.
      const pre = new Set<number>()
      rows.forEach((c, i) => { if (matchIndex(c)) pre.add(i) })
      setSelected(pre)
      setMatchesOnly(pre.size > 0)
    } catch {
      setImportError('Failed to read the file.')
    }
  }

  const toggle = (i: number) =>
    setSelected(prev => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })

  const importSelected = async () => {
    if (!parsed || selected.size === 0) return
    setImporting(true)
    setImportError(null)
    // Skip people we already have (same name + company).
    const existingKeys = new Set(referrals.map(r => `${r.contact_name}|${normCompany(r.company)}`.toLowerCase()))
    const rows = [...selected]
      .map(i => parsed[i])
      .filter(c => !existingKeys.has(`${c.contact_name}|${normCompany(c.company)}`.toLowerCase()))
      .map(c => ({
        user_id:          userId,
        company:          c.company,
        contact_name:     c.contact_name,
        contact_role:     c.contact_role || null,
        contact_linkedin: c.contact_linkedin || null,
        contact_email:    c.contact_email || null,
        status:           'identified',
        connection_type:  'linkedin_1st',
        notes:            matchIndex(c) ? 'LinkedIn connection — you have a live job at this company.' : 'Imported from LinkedIn connections.',
      }))
    if (rows.length === 0) { setImporting(false); setShowImport(false); return }
    const { data, error } = await supabase.from('referral_pipeline').insert(rows).select()
    if (error) {
      setImportError(error.message || 'Import failed.')
      setImporting(false)
      return
    }
    if (data) setReferrals(prev => [...data, ...prev])
    setImporting(false)
    setShowImport(false)
    setParsed(null)
    setSelected(new Set())
  }

  const defaultTemplate = templates.find(t => t.is_default)?.body || ''

  const addContact = async () => {
    if (!newContact.contact_name || !newContact.company) return
    setSaving(true)
    const { data } = await supabase.from('referral_pipeline').insert({
      ...newContact,
      user_id: userId,
    }).select().single()
    if (data) setReferrals(prev => [data, ...prev])
    setNewContact({ status: 'identified' })
    setShowModal(false)
    setSaving(false)
  }

  const updateStatus = async (id: string, status: string) => {
    await supabase.from('referral_pipeline').update({ status }).eq('id', id)
    setReferrals(prev => prev.map(r => r.id === id ? { ...r, status: status as any } : r))
  }

  const copyMessage = (contact: ReferralContact) => {
    const msg = defaultTemplate
      .replace('{name}', contact.contact_name)
      .replace('{role}', 'the relevant role')
      .replace('{company}', contact.company)
    navigator.clipboard.writeText(msg)
    setCopiedId(contact.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const byStatus = (status: string) => referrals.filter(r => r.status === status)

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="flex-1 p-6 max-w-5xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Referral Pipeline</h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">{referrals.length} contacts · track outreach from identification to referral</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setShowImport(true); setParsed(null); setImportError(null) }}
              className="flex items-center gap-2 px-4 py-2 border border-slate-200 dark:border-slate-700
                         text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800
                         text-sm font-medium rounded-lg transition-colors"
            >
              <Upload className="w-4 h-4" /> Import from LinkedIn
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700
                         text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" /> Add Contact
            </button>
          </div>
        </div>

        {/* Pipeline stages */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          {['identified', 'message_sent', 'responded', 'referred'].map(status => (
            <div key={status} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3">
              <div className={clsx('inline-flex px-2 py-0.5 rounded-full text-xs font-medium mb-1.5', STATUS_COLORS[status])}>
                {STATUS_LABELS[status]}
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{byStatus(status).length}</p>
            </div>
          ))}
        </div>

        {/* Contact cards */}
        <div className="space-y-2">
          {referrals.map(contact => (
            <div key={contact.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">{contact.contact_name}</span>
                    <span className="text-slate-400 dark:text-slate-500 text-xs">at</span>
                    <span className="font-medium text-slate-700 dark:text-slate-300 text-sm">{contact.company}</span>
                    {contact.contact_role && (
                      <span className="text-slate-500 dark:text-slate-400 text-xs">· {contact.contact_role}</span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 mt-2">
                    {contact.contact_linkedin && (
                      <a href={contact.contact_linkedin} target="_blank" rel="noopener noreferrer"
                         className="text-blue-500 hover:text-blue-700 text-xs flex items-center gap-1">
                        <Linkedin className="w-3 h-3" /> LinkedIn
                      </a>
                    )}
                    {contact.contact_email && (
                      <a href={`mailto:${contact.contact_email}`}
                         className="text-slate-500 hover:text-slate-700 text-xs flex items-center gap-1">
                        <Mail className="w-3 h-3" /> Email
                      </a>
                    )}
                    {contact.follow_up_date && (
                      <span className="text-amber-600 text-xs">Follow-up: {contact.follow_up_date}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Copy message button */}
                  {defaultTemplate && (
                    <button
                      onClick={() => copyMessage(contact)}
                      className={clsx(
                        'p-1.5 rounded-lg transition-colors text-xs',
                        copiedId === contact.id
                          ? 'bg-green-50 text-green-600'
                          : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
                      )}
                      title="Copy referral message"
                    >
                      {copiedId === contact.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}

                  {/* Status selector */}
                  <select
                    value={contact.status}
                    onChange={e => updateStatus(contact.id, e.target.value)}
                    className={clsx(
                      'text-xs font-medium px-2 py-1 rounded-full border-0 focus:ring-2 focus:ring-indigo-500',
                      STATUS_COLORS[contact.status]
                    )}
                  >
                    {Object.entries(STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {contact.notes && (
                <p className="text-slate-500 dark:text-slate-400 text-xs mt-2 border-t border-slate-100 dark:border-slate-800 pt-2">{contact.notes}</p>
              )}
            </div>
          ))}
        </div>

        {referrals.length === 0 && (
          <div className="text-center py-16 text-slate-400 dark:text-slate-500">
            <p className="font-medium">No referral contacts yet</p>
            <p className="text-sm mt-1">Add connections you're planning to reach out to for referrals</p>
          </div>
        )}
      </main>

      {/* Add Contact Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-900 border border-transparent dark:border-slate-800 rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="font-bold text-lg text-slate-900 dark:text-slate-100 mb-4">Add Referral Contact</h2>
            <div className="space-y-3">
              {[
                { key: 'contact_name',     label: 'Name', required: true },
                { key: 'company',          label: 'Company', required: true },
                { key: 'contact_role',     label: 'Their Role' },
                { key: 'contact_linkedin', label: 'LinkedIn URL' },
                { key: 'contact_email',    label: 'Email' },
                { key: 'notes',            label: 'Notes / How you know them' },
              ].map(({ key, label, required }) => (
                <div key={key}>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1 block">
                    {label}{required && ' *'}
                  </label>
                  <input
                    type="text"
                    value={(newContact as any)[key] || ''}
                    onChange={e => setNewContact(p => ({ ...p, [key]: e.target.value }))}
                    className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg text-sm
                               focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowModal(false)}
                className="flex-1 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
                Cancel
              </button>
              <button onClick={addContact} disabled={saving || !newContact.contact_name || !newContact.company}
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm
                           font-medium rounded-lg disabled:opacity-50 transition-colors">
                {saving ? 'Saving...' : 'Add Contact'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import from LinkedIn Modal */}
      {showImport && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-900 border border-transparent dark:border-slate-800 rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between mb-1">
              <h2 className="font-bold text-lg text-slate-900 dark:text-slate-100">Import from LinkedIn</h2>
              <button onClick={() => setShowImport(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {!parsed ? (
              <div className="mt-3">
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  LinkedIn doesn't allow apps to read your connections, but you can export your own:
                </p>
                <ol className="text-sm text-slate-600 dark:text-slate-400 mt-2 space-y-1 list-decimal list-inside">
                  <li>LinkedIn → <strong>Settings &amp; Privacy → Data Privacy → Get a copy of your data</strong></li>
                  <li>Tick <strong>Connections</strong>, request the archive (usually ready in ~10 min)</li>
                  <li>Unzip it and upload <strong>Connections.csv</strong> below</li>
                </ol>
                <a href="https://www.linkedin.com/mypreferences/d/download-my-data" target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 text-sm mt-2 hover:underline">
                  <Linkedin className="w-3.5 h-3.5" /> Open LinkedIn data export
                </a>

                <label className="mt-4 block border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl
                                  p-6 text-center cursor-pointer hover:border-indigo-400 transition-colors">
                  <Upload className="w-6 h-6 mx-auto text-slate-400 mb-2" />
                  <span className="text-sm text-slate-600 dark:text-slate-300 font-medium">Choose Connections.csv</span>
                  <input type="file" accept=".csv,text/csv" className="hidden"
                         onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f) }} />
                </label>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                  Parsed in your browser — the file isn't uploaded anywhere until you choose who to import.
                </p>
                {importError && <p className="text-sm text-red-600 dark:text-red-400 mt-2">⚠️ {importError}</p>}
              </div>
            ) : (
              <div className="mt-3 flex flex-col min-h-0">
                <div className="flex items-center gap-2 text-sm">
                  <Sparkles className="w-4 h-4 text-indigo-500" />
                  <span className="text-slate-700 dark:text-slate-200">
                    <strong>{matchCount}</strong> of your {parsed.length} connections are at companies in your feed.
                  </span>
                </div>
                <label className="flex items-center gap-2 mt-3 text-sm text-slate-600 dark:text-slate-300">
                  <input type="checkbox" checked={matchesOnly} onChange={e => setMatchesOnly(e.target.checked)} />
                  Show only matches at my companies
                </label>

                <div className="mt-3 overflow-y-auto flex-1 border border-slate-100 dark:border-slate-800 rounded-lg divide-y divide-slate-100 dark:divide-slate-800">
                  {visibleConns.length === 0 ? (
                    <p className="text-sm text-slate-400 p-4 text-center">
                      No connections at your feed companies. Uncheck the filter to browse all {parsed.length}.
                    </p>
                  ) : visibleConns.map(({ c, i, match }) => (
                    <label key={i} className="flex items-center gap-3 p-2.5 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <input type="checkbox" checked={selected.has(i)} onChange={() => toggle(i)} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">{c.contact_name}</span>
                          {match && <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-[10px] font-medium rounded-full whitespace-nowrap">in your feed</span>}
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                          {c.contact_role ? `${c.contact_role} · ` : ''}{c.company}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>

                {importError && <p className="text-sm text-red-600 dark:text-red-400 mt-2">⚠️ {importError}</p>}
                <div className="flex gap-3 mt-4">
                  <button onClick={() => { setParsed(null); setSelected(new Set()) }}
                    className="flex-1 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
                    Back
                  </button>
                  <button onClick={importSelected} disabled={importing || selected.size === 0}
                    className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors">
                    {importing ? 'Importing…' : `Import ${selected.size} contact${selected.size === 1 ? '' : 's'}`}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
