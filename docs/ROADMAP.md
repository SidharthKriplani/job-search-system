# ROADMAP — ideas & backlog

Organised Now / Next / Later. Move items up as they're picked up; log completion
in CHANGELOG.

---

## NOW — get the daily loop producing real jobs on screen
- [ ] Push deps fix; re-run workflow; read the log.
- [ ] Run `supabase/schema.sql` (creates/backfills `user_profiles`).
- [ ] Fill Settings profile (roles, locations, salary floor).
- [ ] Confirm jobs appear in the dashboard, end to end.

## NEXT — make the feed actually relevant + the product sticky
- [ ] **Expand the registry** — add finance / consulting / India companies
      (Greenhouse/Lever/Ashby slugs). Broad coverage is just more one-line entries.
- [ ] **Enable Adzuna** (free keys) → India coverage + salary data.
- [ ] **Scraper-health UI** — surface which sources returned 0 / failed, so silent
      breakage is visible (table already exists).
- [ ] **Intelligence layer (the differentiator):**
  - [ ] Per-job fit score with 2-3 reasons + the gaps (recruiter voice).
  - [ ] CTC-to-ask, grounded per company/level/city (must cite a basis — being
        wrong costs credibility).
  - [ ] One-click tailored resume from the master doc (summary opening locked).
  - [ ] Auto interview-prep brief when a job hits "callback".

## LATER — career OS + product
- [ ] **Activate the referral engine** — "who do I know here", stage-aware
      reminders, auto-drafted referral messages (LinkedIn stays manual).
- [ ] **Retention / career-OS features** — quarterly market/salary pulse,
      relationship-maintenance nudges, passive "watch mode" when not searching.
      (Fixes the transient-problem churn that kills job-search tools.)
- [ ] **Workday connector** — add tenants for finance majors (S&P, Moody's, HSBC…).
- [ ] **Productisation** — if pursued, the wedge is a job-search OS for senior
      Indian professionals; lean on ATS APIs + Gmail, not raw scraping. Hard part
      is retention (see above).

## Parked / won't-do (for now)
- Direct scraping of LinkedIn/Naukri/Indeed — ban risk + fragility (see D1, D5).
- Auto-applying / auto-LinkedIn-messaging — spammy, account risk.
- Indian HRMS portals (Darwinbox, PeopleStrong, Keka) — no public APIs, low signal;
  those companies post to Naukri anyway.
