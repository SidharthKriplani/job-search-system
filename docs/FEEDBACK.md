# FEEDBACK — user observations & what they changed

Log what the user noticed/asked and the resulting action. Newest first. This is
how the product learns its owner's priorities.

---

## 2026-07-15

- **"App refresh works for 3 minutes but the backend job runs longer — this is
  a 2nd refresh running. This is stupid, why did you not check this?"** Right —
  the button's timing model was never validated against a real run. Fixed: real
  ETA (600s), no mid-run give-up, 409 + attach on concurrent trigger, auto-attach
  on page load. _(CHANGELOG 07-15 (d))_

## 2026-06-23

- **"This product is shit / still 0 jobs after refresh."** Feed empty for the
  finance user despite matching being proven correct in tests. Root cause is the
  LIVE scrape pipeline (deploy/DB gap) which we've never observed. → Stopped
  shipping matching changes; need the GitHub Actions **run log** to diagnose
  (SOURCE SUMMARY + the exit-code-1). Logged as the TOP BLOCKER in STATUS.

- **"Why do you keep assuming? She's BACK office, her whole history is back office."**
  Repeatedly mislabelled Shivali (Verity KPO = offshore IB-research SUPPORT =
  back/middle office) as "front office" from surface keywords. Real lesson →
  **finance is one connected market**; cross-linked the finance families (D16) so
  the user never has to pick front-vs-back again.

- **"Can't we scrape finance companies' own boards?"** → Per-PLATFORM connectors
  (D17): built Oracle + SmartRecruiters (EXL/JPMorgan/Jefferies/WNS/NielsenIQ).
  Probed Darwinbox/SuccessFactors/iCIMS/Taleo — the KPOs (Evalueserve/Acuity/
  CRISIL) are captcha-walled; only Naukri/Gmail reaches them (D18).

- **"How do we get past Naukri's engagement model?"** → Explained: don't scrape;
  parse the user's OWN consented Naukri/iimjobs alert emails (apply stays on
  Naukri). The defensible long-tail path (D18).

- **"How do we build test gates / staging to catch regressions?"** → Built the
  pytest suite + CI gate + pre-push script + branch→preview→merge staging.

- **"Now critique yourself ruthlessly… then mentor us with solutions."** Did a
  veteran-style teardown (12 flaws) + a sequenced fix plan. Agreed scope: finance
  + tech only; foundation-first (data model, freshness, tests); then the moat
  (competence engine + feedback loop); then retention.

- **Process asks:** always `cd` into the project before git commands (after a
  stray command tried to add `~/Library`); always verify don't assume.

## 2026-06-22

- **"You might be doing a lot more shit you don't know about — I'll have to surface
  it later."** Stopped relying on brace-counts. Installed deps in the sandbox and
  ran the REAL toolchain: `tsc --noEmit` (0 errors), all Python imports, and filter
  edge-cases → **found + fixed 2 real crash bugs** (NULL profile fields for new
  signups → silent empty feed; NULL job title). _(CHANGELOG 06-22 (c))_

- **"Investment banker → engineers; finance results all foreign; 'india' search
  shows old AI engineers."** Diagnosed: (a) foreign jobs because overseas-drop
  only ran with a location set → **India-default** (D11); (b) engineers leaking via
  broad finance keywords → **precision read-guard** (D14); (c) stale AI rows were a
  deploy-timing artifact (build was red on the Set-iteration errors).

- **"Why do you keep making such mistakes?"** Owned the real repeat mistake: the
  build failed twice on the same Set-iteration class because I patched symptoms.
  Root-caused to a missing `tsconfig` target → fixed once (D15).

- **Folder moved** from `…/GitHub/upskill platforms (4)/…` to
  `…/BreakLabs/career-os/job-search-system` (caused a mid-session access drop).

- **"Refresh done but feed doesn't update till I reload."** The feed list is
  client-fetched; completion only did a server refresh the list ignored. → Refresh
  now hands `onDone` to the dashboard, which re-pulls the feed the instant the run
  finishes (with a short retry). _(CHANGELOG 06-21 (g))_

- **"Roles connect to each other — data scientist → ML/analyst/PM…; finance needs
  more; let me search by sector/keyword too."** → Built the curated role-family
  graph + sector layer; field-dependent (finance gets the keyword net, tech rides
  titles). _(D13)_

- **"Can we fetch someone's LinkedIn connections for referrals?"** → Deep research:
  no compliant API; CSV import is the only consented path. Built it. _(D12)_

- **Multiple "it works wrong" reports.** → Deep multi-pass audit (frontend / Python
  / schema-RLS) — fixed a CRITICAL cross-user score contamination, a latent
  total-batch-loss, salary/location bugs, silent mutation failures, RLS holes,
  duplicate rows. _(CHANGELOG 06-21 (d), AUDITS v2)_

## 2026-06-20

- **"Idle waiting screen, should update at each step."** Refresh button was
  fire-and-forget. → Built live run-status polling (queued/running/done/failed +
  log link). _(D7)_

- **"No other issue would be there now I hope?"** Wanted a forward-looking
  honesty check. → Traced the full run path; hardened the last unguarded call;
  documented remaining *config/data* risks (schema, profile, coverage) vs code.

- **"You are supposed to give me git code… and idk what I want, you tell me."**
  → Provided exact commit/push commands; recommended **go-live before more
  features** (the system had never run end-to-end in production).

- **"Not profile-restricted — make it a real product. If the scraper doesn't
  work, nothing works."** → Reframed around a durable data foundation; built and
  proved the ATS-source ingestion engine (4,309 live jobs). _(D5)_

- **"Don't talk in such an excited tone like you figured out god."** Tone note. →
  Keep responses measured, honest, recruiter/operator voice. No hype.

- **"CTC numbers — I don't want to look like a fool."** Salary figures must be
  accurate and sourced. → Became a product principle: every number cites a basis;
  fixed the salary parser. Informs the future intelligence layer.

- **"Make it ATS-friendly, position for both IC and leadership."** (resume arc) →
  Master resume built; relevant to the future tailored-resume feature.

---

## How to log feedback
One bullet per item: **what they said** → what it changed (link a Decision or
Changelog entry where relevant). Capture tone/positioning feedback too, not just
bugs.

## 2026-07-23 — Sidharth: "working shitty", duplicates visible, everything Strong fit, coverage doubts
- Report: two identical Danaher rows (added 2d vs 3d ago); "Strong fit" on nearly everything;
  42k-row feed overwhelming; dirty scraped titles ("...GenAi/LLM, , MCP"); separately, market
  jobs he sees elsewhere aren't appearing in the feed (coverage gap — NOT fixed this pass).
- Shipped same day (supervisor session, branch feed-v2b): (1) display-level duplicate collapse
  by normalized title+company+location in DashboardClient; (2) fit tiers recalibrated 70/40 ->
  82/58 so Strong is scarce; (3) feed defaults to New-only view (warehouse is opt-in);
  (4) title-hygiene cleanup at the upsert choke point in supabase_client.
- NOT done (needs a schema-aware session): DB-level canonical dedup (URL canonicalization
  re-keys source_job_id -> must ship WITH a one-time duplicate-cleanup migration, else one
  run of full re-insertion); coverage-gap investigation (is the read-guard/role binding
  filtering out real market jobs? sample audit needed vs LinkedIn/Naukri hand-pulls).
