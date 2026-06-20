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

## Expanded catalogue — round 2 (résumé / outreach / gmail / autofill)

### Résumé tailoring + ATS (Prepare, M4)
- **ResumeLM** (`olyaiy/resume-lm`) — ⭐ OSS AI résumé builder, **Next.js 15 + React +
  Tailwind = our exact stack.** Tailors ATS résumés to a JD. Best to borrow/embed.
- **Resume-Tailor-AI** (`JaimeYeung/Resume-Tailor-AI`) — JD-tailoring + aggressive ATS
  pass + clean **no-tables/columns PDF** output. Borrow the ATS-clean output logic.
- **Resume-Matcher** (`srbhr/Resume-Matcher`) — local Ollama OR API LLM; match score +
  keyword gaps. Already in catalogue.
- **Smart ATS** (`Deba951`) — Gemini match % + missing keywords (reference).

### Email finding (Reach, M5)
- **Pyxis**, **giuseppebaldini/email-finder**, **MailFinder** — name+domain → likely
  addresses (already catalogued). Borrow the permutation idea.

### Gmail send / mail-merge (Reach, M5)
- **ErikinBC/gmailAPI** — mail-merge via Gmail API **with attachments** → send the
  tailored résumé from the user's own Gmail. We already have Gmail OAuth; extend to
  `gmail.send`. Borrow.
- **Group Merge** (Google Workspace add-on), **PyAutoMail** — personalised templated
  sends. Reference.

### Job-seeker cold outreach (Reach, M5) — closest peers
- **ColdContactXLSX** (`aasthas2022`) — ⭐ *exactly our use case*: generate recruiter
  emails + customisable templates + personalise, for job seekers. Borrow the flow.
- **Automated-Cold-Email-Outreach-System** (`bhanuteja2001`) — cold emails for job apps
  via **Google Sheets + GitHub Actions** (our exact infra pattern). Reference design.
- **PaulleDemon/Email-automation** — scheduling, follow-up sequences, variable/if
  templates. Borrow follow-up logic.

### Autofill / apply-assist (Apply, M6)
- **Job App Filler** (`berellevy/job_app_filler`) — ⭐ autofills the *painful* ATS forms
  (**Workday, iCIMS**), open source, **no data leaves the browser**. The safe, high-value
  one — extension-based.
- **ApplyEase** (`sainikhil1605/ApplyEase`) — privacy-first Chrome ext, React+FastAPI,
  autofill + tailored answers via **local LLM (Ollama/LM Studio)**. Aligns with our ethos.
- **AIHawk**, **EasyApplyJobsBot**, **AutoApplyMax** — ⚠️ **borrow autofill, NOT mass
  auto-submit.** Spray-and-pray LinkedIn auto-apply = ban risk + recruiters ignore it +
  against our quality-over-quantity principle (cf. "LinkedIn stays manual"). Skip the bots.

### Verdicts (round 2)
| Tool | Verdict |
|------|---------|
| ResumeLM | ⭐ borrow/embed (same stack) — résumé builder + ATS output |
| ColdContactXLSX, gmailAPI | ⭐ borrow — the outreach MVP (find email + template + Gmail send) |
| Job App Filler | borrow — autofill Workday/iCIMS (extension) |
| ApplyEase | reference — local-LLM autofill, privacy-first |
| Auto-apply bots (AIHawk/EasyApply) | ⚠️ skip the auto-submit; ban risk + low quality |

## Expanded catalogue — round 3 (agents / interview / salary)

### End-to-end AI job agents — validate our pipeline; borrow, don't blindly run
- **ApplyPilot** (`Pickle-Pixel/ApplyPilot`) — 6-stage autonomous pipeline (discover →
  score → tailor → cover letter → submit). Same shape as our roadmap — reference.
- **MadsLorentzen/ai-job-search** — ⭐ built **on Claude Code**: fork, fill profile, it
  evaluates jobs / tailors CV / writes cover / preps interviews. Closest to *how we
  work*; great reference for the agent layer.
- **lookr-fyi/job-application-bot-by-ollama-ai** — end-to-end agent on **Ollama (local)**:
  semantic filters + ATS résumés + referrals. Borrow the local-LLM approach.
- **imon333/Job-apply-AI-agent** — Python + n8n + Selenium + OpenAI + Sheets. Reference.
- ⚠️ **The auto-submit half of all of these is the trap** (ban/spam/quality). Borrow the
  *pipeline shape* + *local-LLM*; keep submission human-in-the-loop.

### Interview prep (GRAND-VISION stage; complements the Labs)
- **IliaLarchenko/Interviewer** — ⭐ AI mock tech interview, runs **locally via Ollama**.
  Free/open/local — could power live mock Q&A on top of the Labs' structured prep.
- Next.js + Gemini mock-interview apps (`danielace1`, `modamaan`) — reference UIs.
- **Natively** — local interview copilot / notes, BYOK. (Live-interview assist is
  ethically grey — note, don't necessarily adopt.)

### Salary / comp intel — honest gap
- No strong **India-specific OSS comp dataset** exists. Levels.fyi is crowdsourced (free
  site, not an OSS dataset); GitHub/Kaggle have generic global salary datasets.
- **For India, build/aggregate:** the salary fields **Adzuna already returns** (we have
  the connector) + Glassdoor estimates + (later) our own crowdsourced submissions. This
  is a *build*, not a drop-in.

## Honest research status
Covered (3 rounds): job sources, ATS company lists, semantic matching, résumé
tailoring, email-find, Gmail send, outreach, autofill, AI agents, interview prep,
salary. **Not yet done — per-repo due diligence:** stars / last-commit / license /
code quality for each candidate before we adopt it. That verification happens at
integration time, repo by repo (and is the real "best research" for a given build).

## Sources
- https://github.com/speedyapply/JobSpy
- https://github.com/Feashliaa/job-board-aggregator
- https://github.com/Masterjx9/OpenPostings
- https://github.com/qdrant/fastembed · https://github.com/srbhr/Resume-Matcher
- https://github.com/Gsync/jobsync
- https://github.com/mxskeen/pyxis · https://github.com/giuseppebaldini/email-finder
- https://github.com/AmruthPillai/Reactive-Resume
- https://github.com/olyaiy/resume-lm · https://github.com/JaimeYeung/Resume-Tailor-AI
- https://github.com/ErikinBC/gmailAPI
- https://github.com/aasthas2022/ColdContactXLSX · https://github.com/bhanuteja2001/Automated-Cold-Email-Outreach-System
- https://github.com/PaulleDemon/Email-automation
- https://github.com/berellevy/job_app_filler · https://github.com/sainikhil1605/ApplyEase
- https://github.com/Pickle-Pixel/ApplyPilot · https://github.com/MadsLorentzen/ai-job-search
- https://github.com/lookr-fyi/job-application-bot-by-ollama-ai · https://github.com/imon333/Job-apply-AI-agent
- https://github.com/IliaLarchenko/Interviewer
