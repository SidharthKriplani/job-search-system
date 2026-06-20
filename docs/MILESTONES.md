# MILESTONES

The product ladder. Each milestone has a clear "done when" so we know we've
actually landed it. Update status as we go; detailed tasks live in ROADMAP.md.

| # | Milestone | Done when | Status |
|---|-----------|-----------|--------|
| M1 | **Jobs live on screen** | The daily run writes real jobs and they render in the dashboard. | ✅ Done 2026-06-20 (4,359 jobs) |
| M2 | **A feed worth opening (relevance)** | Most of the feed is roles the user would genuinely apply to. | 🟡 Code done — needs user profile + Adzuna keys |
| M3 | **A score you can trust** | The highest-scored roles are demonstrably the best fits; scores spread meaningfully. | ✅ Scoring rewritten (JD-aware); verify live |
| M4 | **Intelligence layer (the product)** | Clicking a job gives a recruiter-grade fit verdict + gap analysis + CTC-to-ask + one-click tailored resume. | ⬜ |
| M5 | **The workflow actually used** | The user runs one real application through the 18-stage tracker end to end; referral pipeline used. | ⬜ |
| M6 | **It runs itself** | A week of hands-off daily runs; digest email lands; scraper-health visible; user trusts the feed. | ⬜ |
| M7 | **Productize (optional)** | Multi-user onboarding + retention/career-OS features + pricing. | ⬜ Later |

## M2 detail (next up)
Two levers, both needed:
- **Coverage** — expand `ingest/registry.py` with finance / consulting / research /
  India companies (Greenhouse/Lever/Ashby slugs); enable **Adzuna** (free keys →
  India roles + salary data). Today the pool is US-tech + commodity (Kpler).
- **Targeting** — set the real profile in Settings (target roles, locations,
  salary floor) so the filter selects relevant jobs instead of passing everything.

_Why first:_ a full feed of irrelevant jobs is worth ~nothing, and M3/M4 only
mean something once the feed contains the right roles.

## Lesson banked (2026-06-20)
Getting to M1 took longer than the work itself because failures were silent:
a green CI run was hiding a rejected insert (`remote` non-column). Principle going
forward — **make failures loud** (the upsert now logs lost rows) and **diagnose
from the data** (one SQL count beat hours of log-reading).
