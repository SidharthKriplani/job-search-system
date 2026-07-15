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

- [ ] **Data-model normalization (#3)** — split per-user `job_feed` into `jobs`
      (canonical, deduped) + `user_job_matches` (thin: user_id, job_id, score,
      flags). `cap_user_feed` + trimmed rows buy time, but do this before ~10 heavy
      users. Big migration on a LIVE app → stage carefully (branch → preview → cut).
- [ ] **Verify Gmail parsing at scale** — now opt-in and reachable; confirm the
      parser handles real Naukri/iimjobs alert emails (title↔URL pairing bug, D-note).

## NEXT — stickiness + intelligence (the moat)

- [ ] **Act on the feedback loop** — `feed_feedback` + `TUNING_REPORT.md` collect
      "not relevant" signals weekly; read them and tune role-graph weights. Also
      feed is_saved/applied/dismissed into ranking.
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

- [ ] **Honest fit tiers** — Strong/Good/Possible instead of "83%".
- [x] ~~More Workday tenants + Workable adapter~~ → DONE 2026-07-15: workable +
      bamboohr connectors live; 193 harvested Workday tenants gated behind
      `WORKDAY_INCLUDE_HARVESTED` (flip on after normalization).
- [ ] **More Oracle/SmartRecruiters tenants** (OpenJobs dataset still has
      unmined ORC/SR configs).
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
