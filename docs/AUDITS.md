# AUDITS — audit log

Record each audit: date, scope, headline findings, and a link to the detailed
report. Newest first.

---

## 2026-06-20 — Full code audit (v1)
**Scope:** entire repo read; pipeline run in a sandbox; static + dynamic checks.
**Detailed report:** root [`AUDIT.md`](../AUDIT.md).

**Headline findings (all fixed):**
- Daily digest re-sent the entire feed every day (`get_seen_job_ids` defined but
  never used). → now new-only.
- Salary parser turned GCC monthly pay into bogus LPA (e.g. "AED 25000/month" →
  275 LPA), corrupting scores and the salary floor. → returns 0 (unknown) for
  monthly amounts.
- `schema.sql` not idempotent (re-run failed on existing policies) — the root of
  the "partially applied schema". → fully idempotent now.
- Signup trigger created `message_templates` but **not** a `user_profiles` row, so
  email/password users were invisible to the scraper. → combined trigger +
  backfill.
- `naukri_refresh.py` queried non-existent columns. → guarded + columns added.

**Verified false alarms (already correct):**
- Scrapers were all try/except-wrapped; field names consistent end-to-end; all 3
  Supabase server clients import `CookieOptions`; no React component-in-component.
  (The handoff's "scraper pattern" doc was wrong, not the code.)

**Not verifiable from here (needed live access):** live Supabase table state,
real GitHub Actions run, live-app screenshots, Resend domain status.

---

## How to log the next audit
Add a dated section above with: scope, method, findings (fixed vs open), and a
link to any standalone report. Keep findings one line each.
