# FEEDBACK — user observations & what they changed

Log what the user noticed/asked and the resulting action. Newest first. This is
how the product learns its owner's priorities.

---

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
