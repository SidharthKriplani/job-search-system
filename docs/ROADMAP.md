# ROADMAP — ideas & backlog

Organised Now / Next / Later. Move items up as they're picked up; log completion
in CHANGELOG.

---

## ✅ DONE (2026-07-15 session) — the "unblock + productionize" push

- [x] **Live feed unblocked** — root-caused via a self-reporting diag workflow;
      feed went 0 → 24k+. It was infra (deploy/DB), never matching.
- [x] **Deploy/DB visibility gap closed** — `docs/LAST_RUN.md` run reports,
      `run_history` + `scraper_health_history` tables, `/health` page, pool-drop
      alarm + canary matching check.
- [x] **Signup fixed** — bulletproof `handle_new_user` trigger; de-scoped Google
      sign-in (no warning); set/reset-password flow; robust auth errors.
- [x] **Sources ~3× for India** — jobspy Indeed+LinkedIn, adzuna paginated, +48
      India company boards mined from the OpenJobs GitHub dataset, harvested cap
      400→1000, instahyre connector (best-effort).
- [x] **Filters + sort** — Board/Position/Company/Location facets + relevance|date.
- [x] **Egress/storage caps** — trimmed descriptions, `cap_user_feed`, once/day
      resync, public repo (Actions minutes now free).
- [x] **Saved searches + alerts** — save filters; digest reports new matches.
- [x] **Gmail opt-in** — Connect Gmail in Settings (restricted scope only for
      users who want Naukri/iimjobs parsing).

## NOW — the one real ceiling

- [ ] **Data-model normalization (#3)** — SQL READY: `supabase/migrations/
      2026-07-16-user-job-matches.sql` + staged plan in `docs/PLAN-normalization.md`.
      jobs_pool already IS canonical; migration adds user_job_matches + compat view.
      Stage 0 (run SQL, non-destructive) safe now; stages 1-4 = one live session.
- [ ] **Verify Gmail parsing at scale** — now opt-in and reachable; confirm the
      parser handles real Naukri/iimjobs alert emails (title↔URL pairing bug, D-note).

## NEXT — coverage (data-driven, from scripts/detect_ats.py gap report)

- [x] ~~Darwinbox probe~~ → CONFIRMED BLOCKED 2026-07-16: SPA shell loads but
      the /ms/candidateapi/* layer 403s from datacenter IPs (Cloudflare +
      Turnstile). Original verdict stands; the 10 companies stay covered via
      foundit/jobspy/Gmail. Revisit only if infra ever gets residential IPs.
- [x] ~~SuccessFactors CSB connector~~ → DONE 2026-07-16: sf_csb.py live,
      7 tenants, 663 India jobs. Remaining detail: — the
      Career Site Builder search template is SERVER-RENDERED and shared:
      jobs.birlasoft.com/search/?q=&locationsearch=india returns 25 rows/page
      (jobTitle-link markup), LTIMindtree partial; HCLTech/Wipro run customized
      templates needing per-tenant markers. Build: sf_csb.py shared parser +
      per-tenant overrides, prove-or-kill per tenant. ~10 target companies.
- [x] ~~Kula (Cashfree-class)~~ → DONE 2026-07-16: jobs are in the RSC
      flight payload, no browser needed. connectors/kula.py live (Cashfree,
      Plum, CleverTap).
- [ ] **Detector cadence** — run scripts/detect_ats.py monthly in harvest.yml;
      grow data/target_companies.json (user target_companies fields + requests).

## NEXT — stickiness + intelligence (the moat)

- [x] ~~Act on the feedback loop~~ → DONE 2026-07-16: tuning overrides +
      per-user affinity live in filter_and_score (step 9, bounded ×0.5–1.2);
      feedback_report.py mines weekly suggestions for review-then-promote.
- [ ] **Single source of truth for the role graph (#4)** — one JSON both Python +
      TS read; CI drift check (today hand-mirrored `role_graph.py` ↔ `roleGraph.ts`).
- [ ] **Intelligence layer (the differentiator):**
  - [ ] Per-job fit score with 2-3 reasons + gaps (recruiter voice).
  - [ ] One-click tailored resume from the master doc (already done manually).
  - [ ] CTC-to-ask grounded per company/level/city (must cite a basis).
  - [ ] Auto interview-prep brief when a job hits "callback".
- [ ] **Referral engine** — auto-drafted message per matched contact, stage-aware
      reminders.

## LATER — polish + career OS

- [x] ~~Honest fit tiers~~ → DONE 2026-07-16 (Strong/Good/Possible chips,
      exact % on hover). Skills + fingerprint flywheels also live — repost
      chips, skill-gap reasons, and the home insights dashboard now just
      consume accruing data.
- [x] ~~More Workday tenants + Workable adapter~~ → DONE 2026-07-15: workable +
      bamboohr connectors live; 193 harvested Workday tenants gated behind
      `WORKDAY_INCLUDE_HARVESTED` (flip on after normalization).
- [x] ~~More Oracle/SmartRecruiters tenants~~ → DONE 2026-07-15: +36 SR
      companies (~2.3k India postings) mined from OpenJobs + live-verified;
      ORC candidates probed, zero India yield, stays curated.
- [x] ~~Enterprise ATS platforms~~ → DONE 2026-07-15: **Phenom shipped** (4
      tenants, ~515 India jobs); **Eightfold shipped best-effort** (403s
      datacenter IPs); Taleo/iCIMS/SuccessFactors/Careerjet probed + ruled out
      (see RESEARCH-source-expansion.md). Remaining lever: add more verified
      Phenom tenants (POST /widgets probe, keep if totalHits > 0).
- [ ] **Collapse duplicate cards** across sources in the feed UI.
- [ ] **Career OS** — quarterly market/salary pulse, watch-mode when not searching;
      tie into the Labs (GET HIRED here + GET READY).

## Parked / won't-do (for now)

- Direct scraping of LinkedIn/Naukri/Indeed — ban risk + fragility (D1, D5). (Indeed
  + LinkedIn ARE reached via jobspy, which is a maintained lib, not our scraping.)
- LinkedIn connection-graph via API/scraping — no compliant path (D12); CSV only.
- Auto-applying / auto-messaging — spammy, account risk.
- Indian HRMS portals (Darwinbox, PeopleStrong, Keka) — captcha-walled; they post
  to Naukri anyway (reach via Gmail).
- Global-remote job APIs (The Muse, RemoteOK, Jobicy) — verified ~3% India, mostly
  US-remote noise. Rejected.
