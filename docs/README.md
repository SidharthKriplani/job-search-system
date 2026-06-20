# Project spine

This folder is the durable memory of the project. It exists so anyone — a new
developer, a future Claude session, or you in three weeks — can pick the project
up without losing context.

**If you read one file, read [STATUS.md](STATUS.md).** Then come back here.

## Files & what goes where

- **[STATUS.md](STATUS.md)** — the live snapshot. Where we are *right now*: what's
  deployed, what works, what's blocked, the env/secrets checklist. The first
  thing to read and the first thing to update.
- **[CHANGELOG.md](CHANGELOG.md)** — *lineage*. Every meaningful change, dated,
  newest on top, with the "why". The story of how we got here.
- **[DECISIONS.md](DECISIONS.md)** — the *why behind the architecture*. Numbered
  decisions with context and rationale (lightweight ADRs). Append-only.
- **[ROADMAP.md](ROADMAP.md)** — *ideas & backlog*, split Now / Next / Later.
- **[AUDITS.md](AUDITS.md)** — *audit log*. Findings, scores, links to detailed
  reports (e.g. the root `AUDIT.md`).
- **[FEEDBACK.md](FEEDBACK.md)** — *user feedback* and observations, and what each
  one changed.
- **[RUNBOOK.md](RUNBOOK.md)** — *operations*. Deploy steps, environment variables,
  and a troubleshooting guide for the gotchas we've already hit.

## How to keep it alive

A spine only works if it's updated. The rule of thumb:

> After any session that changes the project, spend two minutes updating
> STATUS.md and adding a CHANGELOG entry. Everything else as needed.

Keep entries short and honest. Note what *doesn't* work, not just what does.

## Related root docs (kept for history)

- `HANDOFF.md` — the original handoff brief that started the current arc.
- `AUDIT.md` — the detailed v1 code audit (summarised in AUDITS.md).
- `SETUP.md` — original step-by-step setup guide (superseded in parts by RUNBOOK.md).
- `ingest/README.md` — deep dive on the ingestion engine.
