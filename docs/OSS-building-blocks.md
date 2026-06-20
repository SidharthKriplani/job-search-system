# OSS building blocks

We build on open source and stay open source. The moat isn't any single tool —
it's the **integrated, India-focused, end-to-end workflow**. This is a living
catalogue of open-source pieces mapped to the job-seeker's journey, with honest
verdicts (adopt / borrow-the-idea / skip) and integration notes.

_Principle: each integration is maintenance surface. Add deliberately._

## Journey → tools

### 1. Discover jobs
- **JobSpy** (`speedyapply/JobSpy`) — ✅ **adopted.** Indeed/Naukri/LinkedIn/
  Glassdoor across 60+ countries. Our all-India engine.
- **Feashliaa/job-board-aggregator** — ⭐ **borrow the data.** 1M+ jobs, **20,000+
  company slugs** across Greenhouse/Lever/Ashby/Workday, daily via GitHub Actions.
  Use it to bulk-expand `ingest/registry.py` instead of hand-probing ~50 at a time.
- **Masterjx9/OpenPostings** — OSS ATS aggregator, 80+ ATS platforms. Same use.
- _Ashby company-discovery scripts_ — find/verify Ashby slugs → CSV/JSON.

### 2. Match / rank to fit
- **FastEmbed** (`qdrant/fastembed`, ONNX, no torch) — ✅ **adopted (opt-in).**
  Free local embeddings → semantic match ("ML Engineer" ≈ "Data Scientist"). See
  `utils/embeddings.py`; enable with `USE_EMBEDDINGS=1` + `requirements-embeddings.txt`.
- **Resume-Matcher** (`srbhr/Resume-Matcher`) — borrow ideas; it also uses FastEmbed
  to score résumé vs JD. Validates our approach.
- sentence-transformers / SBERT (all-MiniLM, mpnet) — heavier (torch); FastEmbed
  is the lean equivalent.

### 3. Intelligence (fit verdict / gaps / tailoring) — M4 Stage 2 (deferred)
- **Ollama + small local LLM** (Llama / Qwen / Phi) — self-hosted, $0, fits
  "open + free". The honest path before any paid API.
- Free API tiers (Gemini Flash, Groq, DeepSeek) — if not self-hosting (see
  earlier research). Only ever runs on the top-K shortlist.

### 4. Tailored résumé / cover letter output
- **Reactive Resume** (`AmruthPillai/Reactive-Resume`) — OSS résumé builder; or
  LaTeX/Jinja templating for deterministic output.

### 5. Referral outreach (M5)
- **Pyxis** (`mxskeen/pyxis`) + **email permutators** (`giuseppebaldini/email-finder`)
  — generate a contact's likely email from name+domain. **Borrow the idea**, with
  caveats: SMTP verification needs port 25 (blocked on our hosts), and cold email
  must be low-volume/high-quality, not bulk. Slots into the referral engine.

### 6. Tracking / workflow (M5) — reference designs
- **JobSync** (`Gsync/jobsync`) — self-hosted Next.js tracker + AI résumé review +
  analytics. Closest peer to what we have; mine for UX ideas.
- **JobHunt**, **JobOps**, **ApplyKit** — other self-hosted trackers.

### 7. Reminders / automation
- **Apprise** (multi-channel notifications), **n8n** (you already have it) — glue
  for digests/reminders beyond email.

## Verdicts at a glance
| Tool | Verdict |
|------|---------|
| JobSpy | ✅ adopted |
| FastEmbed | ✅ adopted (opt-in semantic) |
| Feashliaa/job-board-aggregator, OpenPostings | ⭐ next — bulk registry expansion |
| Ollama / free LLM APIs | later (M4 Stage 2) |
| Reactive Resume | later (tailored output) |
| Pyxis / email-finder | with M5 (referrals) — borrow idea |
| JobSync | reference design, don't fork |

## Sources
- https://github.com/speedyapply/JobSpy
- https://github.com/Feashliaa/job-board-aggregator
- https://github.com/Masterjx9/OpenPostings
- https://github.com/qdrant/fastembed · https://github.com/srbhr/Resume-Matcher
- https://github.com/Gsync/jobsync
- https://github.com/mxskeen/pyxis · https://github.com/giuseppebaldini/email-finder
- https://github.com/AmruthPillai/Reactive-Resume
