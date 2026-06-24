# ROADMAP — ideas & backlog

Organised Now / Next / Later. Move items up as they're picked up; log completion
in CHANGELOG.

---

## NOW — unblock the live feed (everything else is downstream of this)
- [ ] **🔴 READ THE RUN LOG.** Live feed is empty though matching is correct in
      tests. Open GitHub Actions → "Daily Job Scraper" → "Run job scrapers" → read
      the `=== SOURCE SUMMARY ===` block + any traceback / exit-code-1. Distinguish:
      code-not-deployed vs sources-returned-0 vs upserted-0 vs Active-users:0 vs crash.
      **No more matching changes until this is read — the matching is not the bug.**
- [ ] **Close the deploy/DB visibility gap** that caused this whole class of "works
      in sandbox, 0 on screen": a "last run summary" row (job counts/errors) + a
      tiny health surface, and a staging Supabase so migrations are tested first.
- [ ] **Naukri/iimjobs Gmail flow** (D18) — the only route to the captcha-walled
      IB-research KPOs (Evalueserve/Acuity/CRISIL). Guided "set alerts → connect
      Gmail → we parse them" + harden the parser. The real finance long-tail unlock.
- [ ] **Role-suggestion empty state** — when a profile matches 0 but adjacent roles
      match many, offer them ("your roles match nothing; these 6 match 80 — switch?")
      instead of an empty wall. (The exact wall Shivali hit.)

## NEXT — fix the foundation (cheap now, brutal later) — from the veteran/mentor pass
_Do these while there's ~one user; they calcify as users grow (AUDITS v3 / mentor)._
- [ ] **Data-model refactor (#3)** — split per-user `job_feed` into `jobs`
      (canonical, deduped) + `user_job_matches` (thin: user_id, job_id, score,
      flags). Current model duplicates job data per user → storage/compute blow-up.
- [ ] **Freshness stamp (#5)** — `profile_version` on each match row; feed shows
      only current-version rows → kills the stale-feed bug class + the read-guard
      band-aid. Falls out of the refactor.
- [ ] **Single source of truth for the role graph (#4)** — move families/aliases/
      sectors to one JSON both Python + TS read; CI check for drift. (Today they're
      hand-mirrored — `role_graph.py` ↔ `roleGraph.ts`.)

## NEXT — make the product sticky + the intelligence layer
- [ ] **Feedback loop (#8)** — feed `is_saved`/`is_applied`/`is_dismissed` into
      ranking (boost similar, down-weight dismissed clusters). Cheapest moat: the
      feed gets smarter per person. Signals are captured but currently unused.
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
- [x] ~~Workday connector + finance tenants~~ — done (27 tenants); also Oracle +
      SmartRecruiters connectors (D17). India-targeted fetch (D19).
- [ ] **Honest fit tiers** — replace "97%" precise scores with Strong/Good/Possible.
- [ ] **More Oracle/SmartRecruiters tenants** — both connectors scale to more firms.
- [ ] **Gmail parser rework** — per-block title↔URL pairing (fix index mismatch).
- [ ] **Feed UX** — pagination is in; consider infinite scroll + saved searches.
- [ ] **Embeddings on by default** once tuned (true synonym matching).

## Parked / won't-do (for now)
- Direct scraping of LinkedIn/Naukri/Indeed — ban risk + fragility (D1, D5).
- LinkedIn connection-graph via API/scraping — no compliant path (D12); CSV import only.
- Auto-applying / auto-LinkedIn-messaging — spammy, account risk.
- Indian HRMS portals (Darwinbox, PeopleStrong, Keka) — no public APIs; they post to Naukri anyway.
