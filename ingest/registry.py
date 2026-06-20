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
    # India / India-GCC companies (verified live)
    ("postman", "Postman"),
    ("groww", "Groww"),
    ("druva", "Druva"),
    ("phonepe", "PhonePe"),
    ("highradius", "HighRadius"),
    ("mongodb", "MongoDB"),
    ("elastic", "Elastic"),
    ("rubrik", "Rubrik"),
    # Global tech
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
    # Bulk-verified batch (2026-06-20) — global SaaS w/ large India GCCs + India cos
    ("datadog", "Datadog"), ("okta", "Okta"), ("twilio", "Twilio"),
    ("clickhouse", "ClickHouse"), ("intercom", "Intercom"), ("fivetran", "Fivetran"),
    ("smartsheet", "Smartsheet"), ("gusto", "Gusto"), ("slice", "slice"),
    ("vercel", "Vercel"), ("newrelic", "New Relic"), ("checkr", "Checkr"),
    ("amplitude", "Amplitude"), ("pendo", "Pendo"), ("sigmoid", "Sigmoid"),
    ("turing", "Turing"), ("launchdarkly", "LaunchDarkly"), ("pagerduty", "PagerDuty"),
    ("cockroachlabs", "Cockroach Labs"), ("airtable", "Airtable"), ("mixpanel", "Mixpanel"),
    ("calendly", "Calendly"), ("starburst", "Starburst"), ("circleci", "CircleCI"),
    ("labelbox", "Labelbox"), ("lattice", "Lattice"), ("planetscale", "PlanetScale"),
    ("dremio", "Dremio"),
]

LEVER = [
    # India companies (verified live)
    ("meesho", "Meesho"),
    ("zeta", "Zeta"),
    ("mindtickle", "Mindtickle"),
    ("cred", "CRED"),
    # Global
    ("netflix", "Netflix"),
    ("spotify", "Spotify"),
    ("kpler", "Kpler"),
    ("mux", "Mux"),
    ("voiceflow", "Voiceflow"),
    ("romerolabs", "Romero Labs"),
]

ASHBY = [
    # India / India-GCC (verified live)
    ("navi", "Navi"),
    ("confluent", "Confluent"),
    ("temporal", "Temporal"),
    ("airbyte", "Airbyte"),
    ("gainsight", "Gainsight"),
    # Global
    ("ramp", "Ramp"),
    ("openai", "OpenAI"),
    ("linear", "Linear"),
    ("mercury", "Mercury"),
    ("vanta", "Vanta"),
    ("runway", "Runway"),
    ("clipboardhealth", "Clipboard Health"),
    ("posthog", "PostHog"),
    ("hex", "Hex"),
    # Bulk-verified batch (2026-06-20)
    ("snowflake", "Snowflake"), ("notion", "Notion"), ("cohere", "Cohere"),
    ("plaid", "Plaid"), ("cerebras", "Cerebras"), ("handshake", "Handshake"),
    ("kong", "Kong"), ("commure", "Commure"), ("perplexity", "Perplexity"),
    ("supabase", "Supabase"), ("clickup", "ClickUp"), ("baseten", "Baseten"),
    ("sentry", "Sentry"), ("modal", "Modal"), ("render", "Render"),
    ("character", "Character.AI"), ("atlan", "Atlan"), ("neon", "Neon"),
    ("materialize", "Materialize"),
]

# Workday tenants: (tenant, wd_number, site, display_name). Each VERIFIED to
# return jobs live. Big global firms with large India GCCs. To add one: open the
# company's Workday careers page, DevTools → Network → find the /wday/cxs/.../jobs
# POST, and copy tenant + wd-number + site path.
WORKDAY = [
    ("nvidia",     "wd5",  "NVIDIAExternalCareerSite", "NVIDIA"),
    ("salesforce", "wd12", "External_Career_Site",     "Salesforce"),
    ("mastercard", "wd1",  "CorporateCareers",         "Mastercard"),
    ("adobe",      "wd5",  "external_experienced",     "Adobe"),
    ("workday",    "wd5",  "Workday",                  "Workday"),
]
