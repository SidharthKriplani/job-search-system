# CLAUDE.md — read this first

This repository keeps a **project spine** in [`docs/`](docs/). Any AI agent or
developer picking this up should start there — it carries the lineage, current
state, decisions, and open work so you don't have to reconstruct context.

**Start every session by reading [`docs/STATUS.md`](docs/STATUS.md)** — it's the
single source of truth for "where are we right now."

## The spine

| File | Purpose |
|------|---------|
| [docs/STATUS.md](docs/STATUS.md)       | Current state: what's live, what works, what's pending, blockers. **Update after every meaningful change.** |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Lineage: dated log of what changed and why. Append new entries on top. |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why we built it this way (architecture + product decisions). Append, don't rewrite. |
| [docs/ROADMAP.md](docs/ROADMAP.md)     | Ideas + backlog, organised Now / Next / Later. |
| [docs/AUDITS.md](docs/AUDITS.md)       | Audit findings over time (links to detailed reports). |
| [docs/FEEDBACK.md](docs/FEEDBACK.md)   | User feedback and observations, and what they led to. |
| [docs/RUNBOOK.md](docs/RUNBOOK.md)     | How to deploy, run, and troubleshoot. Env vars + known gotchas. |

## Maintenance rules (keep the spine alive)

1. **Did state change?** Update `STATUS.md`.
2. **Did you ship something?** Add a `CHANGELOG.md` entry (date, what, why).
3. **Did you make a non-obvious choice?** Add a `DECISIONS.md` entry.
4. **Did the user give feedback or report a bug?** Log it in `FEEDBACK.md`.
5. **Did you run an audit?** Record it in `AUDITS.md`.
6. Keep entries short. A stale spine is worse than a short one.

## What this project is (one paragraph)

A multi-tenant job-search system: a durable **ingestion engine** (`ingest/`)
pulls live jobs from official ATS APIs (Greenhouse/Lever/Ashby) + aggregators +
user-consented Gmail, filters/scores them per user, and serves a Next.js
dashboard (feed, 18-stage application tracker, referral pipeline) backed by
Supabase, with a daily GitHub Actions run. See `docs/` for everything else.
