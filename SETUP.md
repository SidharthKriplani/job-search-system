# Job Search System — Setup Guide

Multi-tenant web app. Users sign in with Google, connect their Gmail, set their search profile — the system scrapes 15+ job sources daily and sends a digest.

**Stack:** Python scrapers → Supabase → Next.js (Vercel) · GitHub Actions cron

---

## Prerequisites

- [Supabase](https://supabase.com) account (free tier)
- [Google Cloud Console](https://console.cloud.google.com) account (free)
- [Vercel](https://vercel.com) account (free tier)
- [Resend](https://resend.com) account (free: 100 emails/day)
- GitHub repo (private)

Estimated setup time: **45–60 minutes**

---

## Step 1 — Supabase Project

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor → New query**
3. Paste the entire contents of `supabase/schema.sql` and click **Run**
4. Note your credentials from **Project Settings → API**:
   - `NEXT_PUBLIC_SUPABASE_URL` (Project URL)
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (anon key)
   - `SUPABASE_SERVICE_KEY` (service_role key — keep this secret)

---

## Step 2 — Google Cloud Console (OAuth)

This is the most involved step. Do it once.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project: **"Job Search System"**
3. Enable APIs:
   - Search for **"Gmail API"** → Enable
4. Go to **APIs & Services → OAuth consent screen**
   - User Type: **External**
   - App name: "Job Search System"
   - Add your email as test user
   - Scopes: add `https://www.googleapis.com/auth/gmail.modify`
5. Go to **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
   - Application type: **Web application**
   - Authorized redirect URIs — add all of these:
     ```
     https://[your-supabase-project].supabase.co/auth/v1/callback
     http://localhost:3000/auth/callback
     https://[your-vercel-domain].vercel.app/auth/callback
     ```
   - Download the JSON and note `client_id` and `client_secret`

6. Go to **Supabase → Authentication → Providers → Google**
   - Enable Google provider
   - Paste your `client_id` and `client_secret`
   - Click Save

---

## Step 3 — Resend (Email Digests)

1. Sign up at [resend.com](https://resend.com)
2. Add and verify your sending domain (or use the onboarding.resend.dev sandbox for testing)
3. Create an API key → copy it
4. Update `DIGEST_FROM_EMAIL` in `utils/email_digest.py` to match your verified domain

---

## Step 4 — GitHub Repository + Secrets

1. Create a new **private** GitHub repo named `job-search-system`
2. Push all files from `job-search-system/` (everything except `frontend/`)
3. Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|--------|-------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Service role key (from Step 1) |
| `GOOGLE_CLIENT_ID` | From Step 2 |
| `GOOGLE_CLIENT_SECRET` | From Step 2 |
| `RESEND_API_KEY` | From Step 3 |
| `NEXT_PUBLIC_APP_URL` | Your Vercel URL (fill in after Step 5) |

---

## Step 5 — Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) → New Project → Import your GitHub repo
2. Set **Root Directory** to `frontend`
3. Add Environment Variables:
   ```
   NEXT_PUBLIC_SUPABASE_URL = [from Step 1]
   NEXT_PUBLIC_SUPABASE_ANON_KEY = [from Step 1]
   NEXT_PUBLIC_APP_URL = https://[your-app].vercel.app
   ```
4. Deploy
5. Go back to GitHub Secrets → update `NEXT_PUBLIC_APP_URL` with your Vercel URL
6. Go back to Google Cloud Console → add your Vercel URL to Authorized redirect URIs

---

## Step 6 — First User Setup (You)

1. Visit your Vercel URL
2. Click **Continue with Google** — approve all permissions including Gmail
3. Go to **Settings** → fill in your profile:
   - Target roles: "research manager", "team lead research", "associate manager"
   - Locations: "Hyderabad", "Bangalore", "Remote"
   - Salary floor: 25 (or whatever your floor is)
   - Industries: "BFSI", "Consulting", "KPO"

4. Set up Gmail job alerts (one-time, 15 min):
   - **Naukri**: My Jobs → Job Recommendations → create alert for your roles + locations
   - **LinkedIn**: Jobs → Job Alerts → create alert
   - **iimjobs**: Browse → set up email notification
   - **NaukriGulf** (if GCC): create alert for GCC locations

5. Create Gmail filter:
   - In Gmail: Settings → Filters → Create new filter
   - **From:** `naukri.com OR linkedin.com OR iimjobs.com OR indeed.com OR naukrigulf.com OR foundit.in OR timesjobs.com`
   - **Do this:** Apply label "Job Alerts" — create label if it doesn't exist

---

## Step 7 — Test the Scraper

1. Go to your GitHub repo → **Actions → Daily Job Scraper → Run workflow**
2. Watch the logs — you should see jobs being found and inserted
3. Go to your Vercel app → Dashboard — jobs should appear

---

## Step 8 — Add More Users

The system is multi-tenant from day one. Any user who visits the app and signs in with Google automatically gets their own isolated job feed and profile. They just need to:
1. Sign in
2. Fill in their settings (roles, locations, salary)
3. Set up their own Gmail alerts and filter

No code changes needed to onboard new users.

---

## Architecture Overview

```
User's Browser
  └─ Signs in with Google OAuth
  └─ Gmail tokens stored in Supabase (encrypted)
  └─ Profile config saved to user_profiles table

GitHub Actions (daily 6am IST / 00:30 UTC)
  └─ main.py reads all active users from Supabase
  └─ For each user, runs all scrapers concurrently:
     ├─ Workday API (24 companies)
     ├─ Greenhouse API (20 companies)
     ├─ Lever API (18 companies)
     ├─ Gmail parser (reads Job Alerts label)
     ├─ iimjobs (BS4 scraper)
     ├─ Foundit / NaukriGulf / Bayt / GulfTalent
     ├─ Instahyre / Cutshort / AmbitionBox
     └─ Shine / TimesJobs
  └─ Filter + score against user profile
  └─ Upsert to job_feed (with dedup)
  └─ Send daily email digest via Resend
  └─ Log scraper health to scraper_health table

Next.js (Vercel)
  └─ /dashboard  — job feed, filters, mark applied
  └─ /applications — 18-stage kanban
  └─ /referrals  — outreach pipeline
  └─ /settings   — profile config + Gmail status
```

---

## Adding New Scrapers

1. Create `scrapers/newsite.py` with a `scrape(profile: Dict) -> List[Dict]` function
2. Return list of dicts matching the job_feed schema (see `lib/types.ts`)
3. Import and add to `SCRAPERS` list in `main.py`
4. That's it — health monitoring and filtering are automatic

## Adding New Workday Companies

In `scrapers/workday.py`, add to `WORKDAY_COMPANIES`:
```python
{"name": "Company Name", "subdomain": "companysubdomain", "path": "PathFromURL", "families": None},
```
Find the subdomain by visiting their Workday careers page URL.

## Adding New Greenhouse Companies

In `scrapers/greenhouse.py`, add to `GREENHOUSE_COMPANIES`:
```python
{"name": "Company Name", "slug": "their-greenhouse-slug"},
```
Find the slug from their Greenhouse URL (e.g., `boards.greenhouse.io/stripe` → slug is `stripe`).

---

## Troubleshooting

**Scraper health errors in dashboard**
Go to GitHub Actions → check the run logs for the failing source.

**Gmail not parsing emails**
Ensure the "Job Alerts" label exists in Gmail and the filter is set up correctly (Step 6).

**No jobs appearing after first run**
Check that your user_profile has target_roles and locations set in Settings.

**Gmail token expired**
Sign out and sign back in — new OAuth tokens are automatically stored.
