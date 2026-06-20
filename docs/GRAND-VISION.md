# GRAND VISION — one Career Operating System

## ★ Core thesis (refined 2026-06-20) — read this first

**This is not a job-search tool. It's a job-targeted *competence engine*.** The job is
just the target that personalises everything; the product is the **transformation**.

> Pick a job → **test** where you actually stand vs its JD → generate a **tailored
> training plan** to close the gap → as you complete (and *pass*) each stage, your
> **résumé grows with what you've genuinely earned** → end with the tailored résumé +
> small, self-doable **application action items**.

Why it's a moat (and not copyable):
- It **inverts the category.** Everyone else optimises *"apply to more jobs, faster"*
  (Huntr, AIHawk, ApplyPilot). This optimises *"become the person who gets the job."*
- It's **honest** — the résumé grows with *tested, earned* competence, not fabricated
  keywords. Auto-appliers can't copy this without the training engine behind it.
- It **requires the Labs** (your unique asset), and it **kills churn** — people stay to
  *level up*, not to spam applications.

### The loop (data flow)
```
1. SELECT  (JSS)   job → JD text + user's master résumé/profile
2. ASSESS  (Labs)  test current level vs JD's skills → gap list {skill, have, need}
3. PLAN    (Labs)  JD + gaps → ordered plan; each stage = Lab modules + a PASS test
4. VERIFY  (Labs)  complete a stage → pass its gating test → skill = EARNED (+ proof)
5. RÉSUMÉ  (JSS)   each EARNED skill unlocks a credible résumé line (with proof);
                   tailored résumé = f(master + verified skills + JD), grows over time
6. ACTIONS (LLM)   per job+progress → small self-doable steps (mini-project, bullet
                   rewrite, referral nudge, apply link)
7. APPLY   (JSS)   when readiness ≥ role bar → apply + 18-stage tracking + outreach
```
**Integrity rule:** a résumé line appears ONLY after its gating test passes — earned,
not clicked. That's the whole product's credibility.

### Who owns what
- **Labs (PAL/MSL/GenAI) = the engine** — assess, generate plan, content, verify.
  (PAL's "JD → 7-day study plan" generator + readiness scoring are the seeds.)
- **JSS = the target + tracker + profile/résumé store** — the lightweight wrapper.
- **Shared = identity (SSO) + one profile** (master résumé + verified-skills + readiness)
  that every property reads.

---

The job-search-system is one half of a machine. The **Labs** are the other half.
Together they're a single, India-first, open-source **Career OS** — and each half
fixes the other's fatal weakness.

## The two halves

**GET HIRED** — `job-search-system` (this repo)
Discover → match → decide → **reach/outreach** → apply → referral → track. The
engine that turns "I want a job" into applications and conversations.

**GET READY** — the Labs (interview-prep / skill systems, by track)
- **Product Analytics Lab (PAL)** — analyst / PM / data: stats, experimentation,
  RCA, metrics, SQL/Python, product sense. 155+ cases, interview simulator,
  **role-readiness score**, and a **"Defense Doc Generator: paste a JD → 7-day
  study plan."** Live, real.
- **ML Systems Lab (MSL)** — ML engineering / MLOps / systems track.
- **GenAI Lab** — LLM / GenAI engineering track.

Same architecture across all (React+Vite, localStorage-first, optional Supabase,
Vercel) — they're already a family (`CROSS_LAB.md`).

## Why they NEED each other

- **Job search is transient → it churns.** Every job tool dies on retention: user
  gets a job, uninstalls. **The Labs are the retention layer** — people study for
  interviews and skills *continuously*, between searches. The Labs keep the user
  when they're not applying.
- **Prep is abstract → it lacks a goal.** The Labs teach skills, but "prep for what?"
  **The job feed gives prep a target** — real, current India JDs to aim at.

So: job search acquires intent; the Labs retain and deepen it; together they
compound.

## The closed loop (the magic)

```
Job feed finds a role you fit 80%        (job-search-system)
   → computes the GAP: JD wants causal inference, you're light there
   → routes you to the exact Lab room: PAL → Stat Foundations (DiD/RDD/IV)
   → you close the gap; PAL readiness score ticks Senior-ready
   → "realistic-shot" on that job upgrades from Stretch → Strong
   → tailored résumé + outreach (job-search) → you apply
   → callback → PAL Interview Simulator + company track → you prep
   → offer.
```

Every box already exists in one repo or the other. The work is **wiring them**, not
building from scratch. PAL's JD→study-plan generator is *already the bridge* — the
job feed just feeds JDs into it.

## The shared spine (how they connect technically — loosely coupled)
Don't merge the codebases. Connect them with three thin contracts:
1. **One identity** — shared Supabase auth (SSO across all properties).
2. **One profile** — résumé + target roles + skills + per-track **readiness scores**
   live in one place (extend this repo's `user_profiles`). Every property reads it.
3. **Deep links + a tiny API** — job-search emits "gap → Lab room" deep links; Labs
   emit readiness scores back. JSON over HTTPS, no shared runtime.

## Flywheels this unlocks
- **Demand → curriculum:** the live JD corpus (167 boards, growing) tells the Labs
  *what India's market actually demands* → Labs teach exactly that → grads apply
  through the job engine. A data flywheel only you have.
- **Readiness → better matching:** the match score stops being résumé-keywords and
  becomes *"are you actually ready for this role?"* (real Lab scores).
- **GenAI Lab dogfoods the AI layer:** your own GenAI work can power the LLM
  features here (tailored résumé, outreach drafts, mock interviews). One stack.

## The one-line pitch
> Naukri shows you jobs. PAL/MSL/GenAI make you good enough for them. **Together they
> find the role, close your gaps, prove you're ready, write the application, find the
> human to email, and walk you to the offer** — India-first, open source.

## Honest cautions
- **Don't merge prematurely.** Keep four apps + one identity/profile API + deep links.
  Coupling the runtimes would be a mistake.
- **Sequence it.** First make *this* product's loop work (M5 + outreach), and ship the
  **shared profile/identity** as the first cross-property contract. The deep-link
  job↔Lab routing is the second. Everything else compounds after.
- This is a multi-quarter arc, not a sprint. But the pieces already exist — that's the
  rare part.

_Next: read MSL + GenAI Lab in depth to map their rooms to job role-types, and define
the shared `user_profiles` contract as the first integration._
