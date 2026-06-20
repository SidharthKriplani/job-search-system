"""
Company → ATS registry.

This is the ownable asset: a map of companies to the ATS they hire on. Each
entry is a (board_slug, display_name) pair. The connectors enumerate these and
call the matching public JSON API — no scraping.

Broad coverage (any role / any geo). Seeded with well-known boards across tech,
fintech, data, and consumer. EXTEND FREELY — adding a company is one line, and
a dead slug simply returns 0 jobs (surfaced in the run summary, never crashes).

How to find a slug:
  Greenhouse → company careers URL contains boards.greenhouse.io/<slug>
  Lever      → jobs.lever.co/<slug>
  Ashby      → jobs.ashbyhq.com/<slug>
"""

# (slug, display_name)
GREENHOUSE = [
    ("stripe", "Stripe"),
    ("databricks", "Databricks"),
    ("airbnb", "Airbnb"),
    ("robinhood", "Robinhood"),
    ("coinbase", "Coinbase"),
    ("dropbox", "Dropbox"),
    ("doordash", "DoorDash"),
    ("instacart", "Instacart"),
    ("brex", "Brex"),
    ("figma", "Figma"),
    ("discord", "Discord"),
    ("reddit", "Reddit"),
    ("pinterest", "Pinterest"),
    ("twitch", "Twitch"),
    ("asana", "Asana"),
    ("cloudflare", "Cloudflare"),
    ("samsara", "Samsara"),
    ("benchling", "Benchling"),
    ("gitlab", "GitLab"),
    ("sofi", "SoFi"),
    ("affirm", "Affirm"),
    ("lyft", "Lyft"),
]

LEVER = [
    ("netflix", "Netflix"),
    ("spotify", "Spotify"),
    ("kpler", "Kpler"),
    ("mux", "Mux"),
    ("voiceflow", "Voiceflow"),
    ("romerolabs", "Romero Labs"),
]

ASHBY = [
    ("ramp", "Ramp"),
    ("openai", "OpenAI"),
    ("linear", "Linear"),
    ("mercury", "Mercury"),
    ("vanta", "Vanta"),
    ("runway", "Runway"),
    ("clipboardhealth", "Clipboard Health"),
    ("posthog", "PostHog"),
    ("hex", "Hex"),
]

# Workday tenants: (base_url, tenant, site, display_name). Verified per-company.
# Left small/seed — Workday needs exact tenant+site, so add cautiously.
WORKDAY = [
    # ("https://spglobal.wd1.myworkdayjobs.com", "spglobal", "Global", "S&P Global"),
]
