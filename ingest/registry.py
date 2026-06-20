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

The curated lists below are the hand-verified core. They're UNIONED at runtime with
our own harvested lists in `data/{ats}_companies.json` (built by ingest/harvester.py
from Common Crawl — license-clean, ours). Use all_greenhouse() / all_lever() /
all_ashby() to get the merged set.
"""

import json
import os

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
    # Batch 2 (2026-06-20)
    ("dataiku", "Dataiku"), ("vonage", "Vonage"), ("contentful", "Contentful"),
    ("webflow", "Webflow"), ("gocardless", "GoCardless"), ("sendbird", "Sendbird"),
    ("descript", "Descript"), ("assemblyai", "AssemblyAI"),
    # Batch 3 (2026-06-20)
    ("anthropic", "Anthropic"), ("adyen", "Adyen"), ("workato", "Workato"),
    ("jetbrains", "JetBrains"), ("qualtrics", "Qualtrics"), ("marqeta", "Marqeta"),
    ("sumologic", "Sumo Logic"), ("yugabyte", "Yugabyte"), ("typeform", "Typeform"),
    ("buildkite", "Buildkite"), ("comet", "Comet"), ("lithic", "Lithic"),
    # Batch 4 — mined from Feashliaa/job-board-aggregator slug list (CC BY-NC),
    # then live-verified here. (Attribution per dataset license; non-commercial.)
    ("curaleaf", "Curaleaf"), ("crunchyroll", "Crunchyroll"), ("cribl", "Cribl"),
    ("crescolabs", "Cresco Labs"), ("d2l", "D2L"), ("crossriverbank", "Cross River Bank"),
    ("customerio", "Customer.io"), ("crexi", "Crexi"), ("cultureamp", "Culture Amp"),
    ("cymulate", "Cymulate"), ("creativex", "CreativeX"), ("crashplan", "CrashPlan"),
    ("creativefabrica", "Creative Fabrica"), ("crossbeam", "Crossbeam"), ("credible", "Credible"),
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
    ("nium", "Nium"),
    ("mistral", "Mistral AI"),
    ("porter", "Porter"),
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
    # Batch 2 (2026-06-20)
    ("airwallex", "Airwallex"), ("elevenlabs", "ElevenLabs"), ("replit", "Replit"),
    ("deepgram", "Deepgram"), ("sanity", "Sanity"), ("livekit", "LiveKit"),
    ("zapier", "Zapier"), ("railway", "Railway"),
    # Batch 3 (2026-06-20)
    ("harvey", "Harvey"), ("sierra", "Sierra"), ("cresta", "Cresta"),
    ("synthesia", "Synthesia"), ("redis", "Redis"), ("camunda", "Camunda"),
    ("pleo", "Pleo"), ("anyscale", "Anyscale"), ("statsig", "Statsig"),
    ("unit", "Unit"), ("moderntreasury", "Modern Treasury"), ("fullstory", "FullStory"),
    ("stream", "Stream"), ("scaler", "Scaler"),
    # Batch 4 — Feashliaa list, verified
    ("dandy", "Dandy"),
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


# ── Harvested lists (our own, from ingest/harvester.py via Common Crawl) ───────
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
# Cap how many harvested boards the daily run uses (sorted by job count), so the
# run stays bounded even as the harvested file grows to thousands. The full file
# is still kept; raise this as the scaling architecture matures.
_MAX_HARVESTED = int(os.environ.get("MAX_HARVESTED_PER_ATS", "400"))


def _harvested(ats: str):
    """Load our harvested {slug: job_count} for an ATS → [(slug, slug)], capped."""
    path = os.path.join(_DATA_DIR, f"{ats}_companies.json")
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        return []
    items = sorted(d.items(), key=lambda kv: kv[1] if isinstance(kv[1], int) else 0, reverse=True)
    return [(s, s) for s, _ in items[:_MAX_HARVESTED]]


def _merge(curated, harvested):
    seen = {s for s, _ in curated}
    out = list(curated)
    for s, n in harvested:
        if s not in seen:
            out.append((s, n))
            seen.add(s)
    return out


def all_greenhouse(): return _merge(GREENHOUSE, _harvested("greenhouse"))
def all_lever():      return _merge(LEVER, _harvested("lever"))
def all_ashby():      return _merge(ASHBY, _harvested("ashby"))
