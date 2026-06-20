# VISION — beyond a job board

The product is **not a job board**. A job board ends at "here are some jobs."
The real problem is everything *after* that — and almost none of it is solved well
for the Indian seeker. The vision: an **open-source career copilot** that carries
you from "I want a job" to "offer accepted," doing the grunt work at each step.

The job feed is just **the front door.** Here's the house.

## The full journey (and what we can build for each)

### 1. Discover ✅ (have)
Jobs from everywhere — ATS source APIs + JobSpy (Indeed/Naukri) + aggregators.

### 2. Match ✅ / 🟡 (have + embeddings)
Profile + résumé, JD-aware, now semantic. Knows *which* jobs are worth your time.

### 3. Decide (the "should I even apply?")
Per job: a **fit verdict + the gaps + realistic-shot (strong/stretch/long-shot)**
+ **CTC-to-ask** + light **company intel** (Glassdoor rating, recent news, is it a
GCC/product/services). Turns a list into decisions. _OSS/LLM: free local LLM (Ollama)
on the shortlist; company data from public sources._

### 4. Prepare
**One-click tailored résumé + cover letter** from your master doc, per job — opening
identity locked, only the relevant edits. _OSS: Reactive Resume / LaTeX templating + LLM._

### 5. Reach — *"what after jobs"* ⭐ THE flagship
This is the half nobody automates and it's where offers actually come from. For a
target job:
1. Identify the right person (recruiter / hiring manager / a 2nd-degree alum).
2. **Find their likely email** from name + company domain (Pyxis / email-permutation).
3. **LLM drafts a personalised outreach** — referral ask or cold intro — in your voice,
   referencing the specific role.
4. **Attach the auto-tailored résumé** (from step 4).
5. **You review, then send from your OWN Gmail** (we already have Gmail OAuth — extend
   to `gmail.send`). 1:1, your identity, not a spam cannon.
6. Logged in the **referral pipeline** with follow-up reminders.

_Honest guardrails:_ low-volume, high-quality, human-in-the-loop (draft → review →
send). Never bulk-blast — that's spam and burns your name. Email verification is
best-effort (port 25 blocked on servers), so we generate likely addresses and let you
pick / accept some bounce, or send via your Gmail which always delivers.

### 6. Apply & Track ✅ (built, needs wiring — M5)
"Mark applied" → the 18-stage tracker; apply-assist / autofill later (Simplify-style).

### 7. Referrals ✅ (built, needs wiring — M5)
Identify → reach (step 5) → track → convert. The referral pipeline becomes *active*.

### 8. Interview prep
When a job hits "callback": **company + role brief, likely questions, STAR stories
auto-drawn from your résumé, a mock Q&A** (LLM), and prep reminders.

### 9. Negotiate
Offer comparison, **salary benchmarks** (Levels-style public data), negotiation scripts.

### 10. Career OS (retention — the anti-churn layer)
Even when *not* searching: quarterly **market/salary pulse**, **network-warm nudges**
("you haven't spoken to your referrer in 5 months"), **skill-gap tracking** vs your
target roles. This is what stops the "found a job → uninstall" churn that kills every
job-search tool.

## Why this can be (mostly) open source
Each stage maps to an OSS building block (see `OSS-building-blocks.md`): JobSpy,
FastEmbed, Ollama, Reactive Resume, Pyxis/email-finder, public salary datasets. **Our
value is the integration + the India focus + the workflow**, not reinventing any one
piece. Keeping it OSS is a feature: trust, self-hostability, community contribution.

## The one-line pitch
> Naukri shows you jobs. This gets you *hired* — it finds the role, proves you fit,
> writes the application, finds the human to email, and tracks it to offer.

## Sequencing (honest)
The flashy stuff (5, 8) is tempting, but order matters:
1. **M5 — wire the workflow** (apply/referral tracking actually used) — the spine of #6/#7.
2. **Outreach MVP (#5)** — email-permutation + LLM draft + Gmail send, human-in-loop.
   This is the highest-wow, most-differentiated piece. Needs the LLM layer.
3. **Decide/Prepare (#3/#4)** — fit verdict + tailored résumé (LLM Stage 2).
4. Interview prep, negotiate, career-OS — later.

Don't build all ten at once. Each is a milestone; the magic is that they compose.
