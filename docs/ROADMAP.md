# ROADMAP — ideas & backlog

Organised Now / Next / Later. Move items up as they're picked up; log completion
in CHANGELOG.

---

## NOW — relevance you can trust + India coverage
- [ ] **India finance/role coverage** — add India sources for finance + general
      (Naukri/foundit finance feeds, Indian fintech ATS boards) so finance/India
      searches return real results, not an honest-but-empty feed. _Top gap._
- [ ] **Deepen the role graph** for the fields testers actually target (ask them);
      it's only as broad as the seeded families in `utils/role_graph.py`.
- [ ] **Diagnose the daily-run exit-code-1** — get the run log; likely a per-source
      or Resend (unverified domain) error.
- [ ] Verify the latest deploy end-to-end: change role → feed re-matches; search →
      hits DB; refresh → auto-populates; new signup → non-empty feed.

## NEXT — make the product sticky + the intelligence layer
- [ ] **Scraper-health UI** — surface which sources returned 0 / failed (table
      already exists; dashboard shows only a banner).
- [ ] **Resend domain verification** so digests actually send.
- [ ] **Intelligence layer (the differentiator / moat):**
  - [ ] Per-job fit score with 2-3 reasons + the gaps (recruiter voice).
  - [ ] Job-targeted competence engine — test/plan against a role, earned résumé,
        small self-doable action items. (The role graph is the seed of this.)
  - [ ] CTC-to-ask, grounded per company/level/city (must cite a basis).
  - [ ] One-click tailored resume from the master doc.
  - [ ] Auto interview-prep brief when a job hits "callback".
- [ ] **Referral engine** — auto-drafted referral message per matched contact,
      stage-aware reminders (LinkedIn stays manual / CSV-based).

## LATER — career OS + product
- [ ] **Retention / career-OS features** — quarterly market/salary pulse,
      relationship-maintenance nudges, passive "watch mode" when not searching.
- [ ] **Tie into the Labs** (Product Analytics / ML Systems / GenAI) as one Career
      OS: GET HIRED (this) + GET READY (Labs), shared identity + profile.
- [ ] **Workday connector** — add tenants for finance majors (S&P, Moody's, HSBC…).
- [ ] **Gmail parser rework** — per-block title↔URL pairing (fix index mismatch).
- [ ] **Feed UX** — pagination is in; consider infinite scroll + saved searches.
- [ ] **Embeddings on by default** once tuned (true synonym matching).

## Parked / won't-do (for now)
- Direct scraping of LinkedIn/Naukri/Indeed — ban risk + fragility (D1, D5).
- LinkedIn connection-graph via API/scraping — no compliant path (D12); CSV import only.
- Auto-applying / auto-LinkedIn-messaging — spammy, account risk.
- Indian HRMS portals (Darwinbox, PeopleStrong, Keka) — no public APIs; they post to Naukri anyway.
