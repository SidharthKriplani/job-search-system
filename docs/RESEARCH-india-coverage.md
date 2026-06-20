# Research — comprehensive India job coverage (2026-06-20)

Goal: cover **all India jobs, any field** — not a curated company list, not just
finance. What follows is what's actually viable, ranked, with sources.

## Verdict / what we adopted

1. **JobSpy** (`python-jobspy`) — **adopted as the primary all-India engine.**
   Maintained library that scrapes Indeed, **Naukri**, LinkedIn, Glassdoor, Google
   across 60+ countries incl. India, in one call. Pip-installable, returns a clean
   DataFrame with title/company/location/date/salary/type. Verified live: pulled
   general Bangalore/Mumbai jobs across every sector (sales, engineering, audit,
   FPGA…), posted same-day. It IS scraping, but community-maintained and far more
   durable than hand-rolled scrapers; wrapped failsafe (errors → [], run continues).
   _Risk:_ datacenter IPs (GitHub runner) may get throttled by Indeed — watch the
   run summary count; if low, fall back to Adzuna/Apify.
   - https://github.com/speedyapply/JobSpy · https://pypi.org/project/python-jobspy/

2. **Adzuna India** — **connector ready, needs free keys.** Official REST API,
   `api.adzuna.com/v1/api/jobs/in/search/1?app_id=…&app_key=…`. Broad India +
   real salary data. Free tier. Set `ADZUNA_APP_ID` / `ADZUNA_APP_KEY`.
   - https://developer.adzuna.com/

3. **ATS source APIs (already in engine)** — Greenhouse/Lever/Ashby. Mostly
   US/global, but real Indian companies exist there (added: Postman, Groww, Druva,
   Meesho, Zeta, Mindtickle, CRED). To scale the registry to thousands of boards
   (incl. India) use these public lists/repos:
   - https://github.com/Feashliaa/job-board-aggregator (1M+ jobs, 20k+ companies)
   - https://github.com/plibither8/jobber (Ashby/Greenhouse/Lever/BambooHR API)
   - https://github.com/adgramigna/job-board-scraper

4. **Apify actors (paid, reliable) — fallback if JobSpy gets blocked.** Managed
   Naukri scrapers, pay-per-result (~$0.002–0.005/job), no IP/anti-bot hassle:
   - `muhammetakkurtt/naukri-job-scraper`, `memo23/naukri-scraper`,
     `thirdwatch/naukri-jobs-scraper` (all on apify.com)

## Not adopted (and why)
- Hand-rolling Naukri/LinkedIn/Indeed scrapers — fragile, ban risk (the original
  10 portal scrapers we already removed).
- SerpApi Google Jobs — aggregates everything incl. India, but paid per search.
  Worth revisiting if we want Google-for-Jobs breadth.

## Coverage stack now
`JobSpy (Indeed/Naukri India, any field)` + `Adzuna India (+salary)` +
`Greenhouse/Lever/Ashby (global + some India cos)` + `Remotive/Arbeitnow (remote)`
+ `user Gmail (Naukri/LinkedIn alerts)`. The per-user profile filter then narrows
the pool to what's relevant.
