# FEEDBACK — user observations & what they changed

Log what the user noticed/asked and the resulting action. Newest first. This is
how the product learns its owner's priorities.

---

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
