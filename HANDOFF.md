# Job Search System — Opus Handoff Brief

## What You Are Taking Over

A **multi-tenant job search automation SaaS** built for Sidharth Kriplani and friends (5+ users).
The system scrapes 15+ job portals + ATS APIs daily, scores jobs against each user's profile,
and delivers a daily email digest. It also tracks applications (18-stage pipeline) and referrals.

**Owner:** Sidharth Kriplani (sidharthkriplani@gmail.com)  
**Folder to mount:** `~/Documents/Professional/GitHub/upskill platforms (4)/job-search-system`  
**GitHub repo:** https://github.com/SidharthKriplani/job-search-system  
**Live app:** https://job-search-system-zeta.vercel.app  
**Supabase project:** `dnczgcrgaczjhinrplpy` (ap-southeast-1, Singapore)

---

## Architecture Overview

```
GitHub Actions (cron 00:30 UTC = 6am IST)
    └── main.py
        ├── Fetches all active users from Supabase (service role key)
        ├── For each user: ThreadPoolExecutor runs all scrapers in parallel
        │   ├── workday.py       — 24 companies (HSBC, Goldman, JP Morgan, etc.)
        │   ├── greenhouse.py    — 20 companies (Kroll, Lazard, Morningstar, etc.)
        │   ├── lever.py         — 18 companies (Anthropic, OpenAI, Canva, etc.)
        │   ├── gmail_parser.py  — reads "Job Alerts" Gmail label via OAuth
        │   ├── iimjobs.py       — HTML scraper (BS4)
        │   ├── foundit.py       — JSON API
        │   ├── naukrigulf.py    — JSON API (GCC only)
        │   ├── bayt.py          — HTML scraper (GCC only)
        │   ├── gulftalent.py    — HTML scraper (GCC only)
        │   ├── instahyre.py     — JSON API
        │   ├── cutshort.py      — JSON API
        │   ├── ambitionbox.py   — HTML scraper
        │   ├── shine.py         — HTML scraper
        │   └── timesjobs.py     — HTML scraper
        ├── filter_and_score()   — role/location/salary/source scoring (0–1)
        ├── deduplicate()        — by (normalised_title, normalised_company)
        ├── upsert_jobs()        — Supabase, conflict ignore
        └── send_daily_digest()  — via Resend API

Next.js 14 App Router (Vercel)
    ├── / (login)                — email/password + Google OAuth
    ├── /dashboard               — job feed, source filter pills, stats
    ├── /applications            — 18-stage kanban tracker
    ├── /referrals               — referral pipeline + message templates
    ├── /settings                — user profile config (roles, locations, salary)
    └── /auth/callback           — Supabase OAuth handler + Gmail token storage

Supabase (PostgreSQL + Auth + RLS)
    Tables: user_profiles, gmail_tokens, job_feed, applications,
            referral_pipeline, message_templates, contacts, scraper_health
    All tables have RLS. Scrapers use service_role key to bypass RLS.
```

---

## Services Configured

| Service | Status | Notes |
|---------|--------|-------|
| Supabase | ✅ Live | Project `dnczgcrgaczjhinrplpy`, Singapore |
| Vercel | ✅ Live | `job-search-system-zeta.vercel.app` |
| GitHub Actions | ✅ Configured | Runs 6am IST daily + manual trigger |
| Resend | ✅ Key added | Email digests |
| Google OAuth | ✅ Working | Published to production (unverified — shows warning screen) |
| Gmail API | ✅ Enabled | Scope: `gmail.modify` |

### GitHub Secrets (all set)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `RESEND_API_KEY`
- `NEXT_PUBLIC_APP_URL` = `https://job-search-system-zeta.vercel.app`

### Vercel Env Vars (all set)
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `RESEND_API_KEY`
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`

### Google Cloud OAuth
- Project: `job-search-system-500009`
- Client ID: `1068175372256-kp1j8q7ort5juurch4qahlt4jj86d190.apps.googleusercontent.com`
- Authorised redirect URIs:
  - `https://dnczgcrgaczjhinrplpy.supabase.co/auth/v1/callback`
  - `https://job-search-system-zeta.vercel.app/auth/callback`
- Publishing status: **In production** (unverified — users see "unsafe app" warning)
- Billing verification: **Under review** (manual docs submitted, DigiLocker bypassed)

---

## File Structure

```
job-search-system/
├── main.py                          # GitHub Actions entry point
├── naukri_refresh.py                # Playwright Naukri profile refresher (optional)
├── requirements.txt                 # Python deps
├── supabase/
│   └── schema.sql                   # Full DB schema (8 tables, RLS, triggers)
├── scrapers/
│   ├── workday.py, greenhouse.py, lever.py
│   ├── gmail_parser.py
│   ├── iimjobs.py, foundit.py, naukrigulf.py
│   ├── bayt.py, gulftalent.py
│   ├── instahyre.py, cutshort.py, ambitionbox.py
│   ├── shine.py, timesjobs.py
│   └── __init__.py
├── utils/
│   ├── supabase_client.py           # get_active_users, upsert_jobs, etc.
│   ├── filter.py                    # filter_and_score, deduplicate_across_sources
│   ├── email_digest.py              # Resend HTML email
│   └── __init__.py
├── .github/workflows/
│   └── daily.yml                    # Cron + manual trigger
└── frontend/                        # Next.js 14 App Router
    ├── app/
    │   ├── page.tsx                 # Login (email/password + Google OAuth)
    │   ├── layout.tsx
    │   ├── globals.css
    │   ├── auth/callback/route.ts   # OAuth callback + Gmail token storage
    │   ├── dashboard/
    │   │   ├── page.tsx
    │   │   └── DashboardClient.tsx  # Job feed, source filters, stats
    │   ├── applications/
    │   │   ├── page.tsx
    │   │   └── ApplicationsClient.tsx  # 18-stage tracker
    │   ├── referrals/
    │   │   ├── page.tsx
    │   │   └── ReferralsClient.tsx
    │   └── settings/
    │       ├── page.tsx
    │       └── SettingsClient.tsx   # Tag inputs for roles/locations/industries
    ├── components/
    │   ├── Sidebar.tsx
    │   └── JobCard.tsx
    ├── lib/
    │   ├── supabase.ts              # Browser client
    │   ├── supabase-server.ts       # Server client (with CookieOptions fix)
    │   └── types.ts                 # All TypeScript types
    ├── middleware.ts                 # Auth protection + redirects
    ├── tailwind.config.js
    ├── postcss.config.js
    └── package.json
```

---

## What Is Working

- ✅ Google OAuth sign-in (with "unsafe app" bypass — click Advanced → Continue)
- ✅ Email/password sign-up and sign-in
- ✅ Auth redirects correctly to dashboard after login
- ✅ Supabase RLS, user isolation
- ✅ Settings page — tag inputs for roles/locations/industries (cursor focus bug just fixed, not yet deployed)
- ✅ Gmail shown as connected in Settings
- ✅ Job feed UI renders (empty — scraper not run yet)
- ✅ Applications page renders
- ✅ GitHub Actions workflow configured and secrets set
- ✅ Daily cron at 6am IST

---

## Known Bugs / Outstanding Issues (Priority Order)

### CRITICAL — Fix before first real scraper run

1. **Scraper has never been run — profile needed first**
   - Sidharth has not filled in Settings yet (Target Roles, Locations etc.)
   - Scrapers use profile to filter — empty profile = irrelevant or no results
   - **Action:** Fill in Settings, then manually trigger GitHub Actions

2. **Supabase schema partially applied — verify all tables exist**
   - Schema run errored with "policy already exists" the first time
   - A simplified trigger was applied as a hotfix (only inserts user_profile, not message_templates)
   - **Action:** Run this in Supabase SQL Editor and check all 8 tables exist:
     ```sql
     SELECT table_name FROM information_schema.tables
     WHERE table_schema = 'public' ORDER BY table_name;
     ```
   - Expected: applications, contacts, gmail_tokens, job_feed, message_templates,
     referral_pipeline, scraper_health, user_profiles

3. **email_digest.py — Resend integration untested**
   - Never actually fired. Unknown if HTML template renders, if Resend key works,
     if sender domain is verified on Resend.
   - **Action:** Check Resend dashboard for a verified sender domain.
     Resend requires `from:` to use a verified domain, not just any email.

4. **gmail_parser.py — never tested end-to-end**
   - Requires user to have Gmail connected AND have set up job alert filters
     in their Gmail (Naukri, LinkedIn alerts → labelled "Job Alerts")
   - The OAuth token is stored in `gmail_tokens` table after Google sign-in
   - **Action:** Verify token exists: Supabase → Table Editor → gmail_tokens

### HIGH — UX broken or incomplete

5. **Tag input cursor bug fix not deployed yet**
   - `SettingsClient.tsx` was fixed (TagList moved outside parent component)
   - `page.tsx` was fixed (friendly error messages + useSearchParams)
   - **Action:** `git add -A && git commit -m "Fix cursor + error UX" && git push origin main`
   - Git command (run from repo root, remove lock first):
     ```bash
     rm -f ".git/index.lock"
     git add frontend/app/settings/SettingsClient.tsx frontend/app/page.tsx
     git commit -m "Fix: tag input focus loss + friendly login error messages"
     git push origin main
     ```

6. **No dark mode**
   - App is entirely light-themed. Tailwind `darkMode` not configured.
   - Sidharth asked for it.
   - **Action:** Add `darkMode: 'class'` to `tailwind.config.js`, add dark variants
     to all components, add a toggle button in Sidebar.

7. **Applications page — untested**
   - Code exists and compiles, but never tested with real data
   - The 18-stage dropdown, add modal, stage change — all untested
   - **Action:** Manually add a test application and verify all interactions work

8. **Referrals page — untested**
   - Same situation as Applications
   - **Action:** Manual smoke test

9. **Google OAuth "unverified app" warning**
   - All users see "This app isn't verified" and must click Advanced → Continue
   - Permanent fix requires Google verification (4–6 weeks, needs billing verified)
   - Billing verification is under review by Google (manual docs submitted)
   - **Short-term:** Nothing to do, just inform users to click "Advanced"
   - **Long-term:** Complete Google verification once billing clears

### MEDIUM — Missing features

10. **No mobile responsiveness**
    - Dashboard/Settings/Applications use desktop-only layouts
    - Sidebar collapses poorly on small screens

11. **Scraper health dashboard**
    - `scraper_health` table exists but no UI to view it
    - Users can't see which scrapers are failing

12. **No way to manually trigger scraper from UI**
    - Currently: GitHub → Actions → Run workflow
    - Better: "Refresh Now" button in dashboard that calls a webhook

13. **No email confirmation disabled**
    - Supabase email confirmation may still be on
    - New users signing up with email/password may be stuck waiting for confirm email
    - **Action:** Supabase → Authentication → Providers → Email → disable "Confirm email"

14. **`NEXT_PUBLIC_APP_URL` points to wrong URL**
    - Currently set to `https://job-search-system.vercel.app` in GitHub secrets
    - Actual live URL is `https://job-search-system-zeta.vercel.app`
    - Email digest links will be broken
    - **Action:** Update GitHub secret `NEXT_PUBLIC_APP_URL` to correct URL

---

## Immediate Next Steps (in order)

1. Deploy pending code fixes: `git add / commit / push` (see bug #5)
2. Verify all 8 Supabase tables exist (see bug #2)
3. Disable email confirmation in Supabase (see bug #13)
4. Fix `NEXT_PUBLIC_APP_URL` GitHub secret (see bug #14)
5. Check Resend sender domain (see bug #3)
6. Fill in Sidharth's profile in Settings (roles, locations, etc.)
7. Manually trigger GitHub Actions scraper run
8. Verify jobs appear in dashboard feed
9. Add dark mode
10. Smoke test Applications + Referrals pages

---

## Tech Stack Reference

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS, @supabase/ssr |
| Backend (scrapers) | Python 3.11, requests, BeautifulSoup4, google-api-python-client |
| Database | Supabase (PostgreSQL), Row Level Security |
| Auth | Supabase Auth — email/password + Google OAuth |
| Hosting | Vercel (frontend), GitHub Actions (scrapers) |
| Email | Resend API |
| Gmail | Google Gmail API, oauth2 token stored in Supabase |

---

## Key Code Patterns

### Supabase server client (CookieOptions required)
```typescript
import { createServerClient, type CookieOptions } from '@supabase/ssr'
setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[])
```
This pattern must be used in `supabase-server.ts`, `middleware.ts`, and `auth/callback/route.ts`.

### Scraper pattern
```python
def scrape(profile: Dict) -> List[Dict]:
    # returns list of job dicts with keys:
    # source, source_job_id, title, company, location, url, salary_min, salary_max, description
```

### Job upsert (conflict = ignore, keyed on user_id + source + source_job_id)
```python
sb.upsert_jobs(user_id, jobs)  # batches of 100, ON CONFLICT DO NOTHING
```

---

## What NOT To Touch Without Testing

- `supabase/schema.sql` — the schema was partially applied; re-running the full file
  will fail on existing policies. Use `DROP ... IF EXISTS` before any changes.
- `scrapers/gmail_parser.py` — touches live Gmail. Test with a throwaway account first.
- `utils/supabase_client.py` — uses service role key, bypasses all RLS. Be careful.
