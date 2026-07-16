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
    ("doordashusa", "DoorDash"),  # slug moved from "doordash" (404) — live-verified 2026-07-15, 459 jobs
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
    # benchling moved Greenhouse→Ashby 2026-07-15 (added to ASHBY below)
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
    # moved from Ashby → Greenhouse (live-verified 2026-07-15, 103 jobs)
    ("cresta", "Cresta"),
    # India-verified from OpenJobs dataset mining (2026-07-15, live-checked):
    ("globalhealthcareexchangeinc", "Globalhealthcareexchangeinc"), ("imc", "Imc"), ("roblox", "Roblox"),
    ("conga", "Conga"), ("techholding", "Techholding"), ("definitivehcindia", "Definitivehc"),
    ("pay2dc", "Pay2Dc"), ("globalizationpartners", "Globalizationpartners"), ("ethernovia", "Ethernovia"),
    ("putnamassociatesllc", "Putnamassociatesllc"), ("innophaseiot", "Innophaseiot"), ("blenheimchalcotindia", "Blenheimchalcot"),
    ("arcadiacareers", "Arcadiacareers"), ("moniepoint", "Moniepoint"), ("oportun", "Oportun"),
    ("jumio", "Jumio"), ("zinnia", "Zinnia"), ("arkoselabs", "Arkoselabs"),
    ("onarchipelago", "Onarchipelago"), ("atariinc", "Atariinc"), ("hightouch", "Hightouch"),
    ("gatherai", "Gatherai"), ("merqube", "Merqube"), ("instabase", "Instabase"),
    ("kraftonindia", "Krafton"), ("headoutlinkedin", "Headoutlinkedin"), ("tellius", "Tellius"),
    ("fluxon", "Fluxon"), ("anydesk", "Anydesk"), ("prophecysimpledatalabs", "Prophecysimpledatalabs"),
    ("poppulo", "Poppulo"), ("goguardian", "Goguardian"), ("spauldingridge", "Spauldingridge"),
    # From the ATS detector (scripts/detect_ats.py) over target_companies.json,
    # live-verified 2026-07-16 (job counts in comments):
    ("razorpaysoftwareprivatelimited", "Razorpay"),  # 19
    ("glance", "Glance"),                            # 38
    ("observeai", "Observe.AI"),                     # 16
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
    # removed 2026-07-15 (live-verified 404 on Lever):
    #   mux → moved to Ashby (jobs.ashbyhq.com/mux, covered via harvested list)
    #   voiceflow, romerolabs → board gone on Lever/Greenhouse/Ashby
    ("nium", "Nium"),
    ("mistral", "Mistral AI"),
    ("porter", "Porter"),
    # India-verified from OpenJobs dataset mining (2026-07-15, live-checked):
    ("brillio-2", "Brillio"), ("dnb", "Dnb"), ("drivetrain", "Drivetrain"),
    ("coupa", "Coupa"), ("netomi", "Netomi"), ("highspot", "Highspot"),
    ("extremenetworks", "Extremenetworks"), ("bounteous", "Bounteous"), ("actian", "Actian"),
    ("entrata", "Entrata"), ("regrello", "Regrello"), ("levelai", "Levelai"),
    ("matchgroup", "Matchgroup"), ("aeratechnology", "Aeratechnology"), ("findem", "Findem"),
    # From the ATS detector, live-verified 2026-07-16:
    ("paytm", "Paytm"),   # 238 jobs
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
    # removed 2026-07-15: clipboardhealth 404 on Ashby/Greenhouse/Lever (own careers site now)
    ("posthog", "PostHog"),
    ("hex", "Hex"),
    ("benchling", "Benchling"),  # moved from Greenhouse (live-verified 2026-07-15, 50 jobs)
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
    # removed 2026-07-15: cresta → moved to Greenhouse (added there); statsig 404 on all 3 ATSes
    ("harvey", "Harvey"), ("sierra", "Sierra"),
    ("synthesia", "Synthesia"), ("redis", "Redis"), ("camunda", "Camunda"),
    ("pleo", "Pleo"), ("anyscale", "Anyscale"),
    ("unit", "Unit"), ("moderntreasury", "Modern Treasury"), ("fullstory", "FullStory"),
    ("stream", "Stream"), ("scaler", "Scaler"),
    # Batch 4 — Feashliaa list, verified
    ("dandy", "Dandy"),
    # From the ATS detector, live-verified 2026-07-16:
    ("sarvam", "Sarvam AI"),  # 63 jobs
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

    # ── Finance / banking / consulting (verified 2026-06-22; India counts noted).
    # Traditional finance doesn't use Greenhouse/Lever/Ashby — it's on Workday +
    # company portals. These are the GCC / finance-data / bank India pipelines.
    ("statestreet",       "wd1",  "Global",                       "State Street"),    # ~349 India
    ("db",                "wd3",  "DBWebsite",                    "Deutsche Bank"),   # ~264
    ("lseg",              "wd3",  "Careers",                      "LSEG"),            # ~227
    ("wf",                "wd1",  "WellsFargoJobs",               "Wells Fargo"),     # ~221 (Hyd/Blr/Chn)
    ("pwc",               "wd3",  "Global_Experienced_Careers",   "PwC"),             # ~210
    ("visa",              "wd5",  "Visa",                         "Visa"),            # ~160
    ("ntrs",              "wd1",  "NorthernTrust",                "Northern Trust"),  # ~132
    ("morningstar",       "wd5",  "Americas",                     "Morningstar"),     # ~77
    ("blackrock",         "wd1",  "BlackRock_Professional",       "BlackRock"),       # ~48
    ("nasdaq",            "wd1",  "Global_External_Site",         "Nasdaq"),          # ~42
    ("spgi",              "wd5",  "SPGI_Careers",                 "S&P Global"),      # ~37
    ("barclays",          "wd3",  "External_Career_Site_Barclays","Barclays"),        # ~37
    ("synchronyfinancial","wd5",  "careers",                      "Synchrony"),       # ~37
    ("broadridge",        "wd5",  "Careers",                      "Broadridge"),      # ~32
    ("fiserv",            "wd5",  "EXT",                          "Fiserv"),          # ~28
    ("fmr",               "wd1",  "FidelityCareers",              "Fidelity"),        # ~27
    ("capitalone",        "wd12", "Capital_One",                  "Capital One"),     # ~20
    ("fis",               "wd5",  "SearchJobs",                   "FIS"),             # ~3

    # ── Bank IB-research / markets-analytics GCCs in India (verified 2026-06-22).
    # These hire the offshore IB-research / capital-markets / risk-analytics roles
    # (the KPO/GCC support function). Indian-HQ KPOs (Evalueserve, Acuity, CRISIL,
    # SG Analytics) are on Darwinbox/custom with NO public API → Naukri/Gmail route.
    ("citi",  "wd5",  "2",                    "Citi"),                 # ~33 India/page, strong analytics
    ("ms",    "wd5",  "External",             "Morgan Stanley"),       # ~37 India/page, QR/capital markets
    ("ghr",   "wd1",  "lateral-ba_continuum", "Bank of America"),      # Continuum India GCC
    ("factset","wd108","FactSetCareers",      "FactSet"),              # financial-data India (Hyderabad)

    # India-verified from OpenJobs Workday mining (2026-07-15):
    ("maersk", "wd3", "Maersk_Careers", "Maersk"), ("intel", "wd1", "External", "Intel"),
    ("sabre", "wd1", "SabreJobs", "Sabre"), ("aptiv", "wd5", "APTIV_CAREERS", "Aptiv"),
    ("ebay", "wd5", "apply", "eBay"), ("zelis", "wd1", "ZelisCareers", "Zelis"),
    ("crowdstrike", "wd5", "crowdstrikecareers", "CrowdStrike"), ("motorolasolutions", "wd5", "Careers", "Motorola Solutions"),
    ("unisys", "wd5", "External", "Unisys"), ("hp", "wd5", "ExternalCareerSite", "HP"),
    ("dentsuaegis", "wd3", "DAN_GLOBAL", "Dentsu"), ("rollsroyce", "wd3", "professional", "Rolls-Royce"),
    ("travelhrportal", "wd1", "Jobs", "Travelhrportal"), ("issgovernance", "wd1", "ISScareers", "ISS"),
    ("mrisoftware", "wd501", "External_CareerSite", "MRI Software"), ("illumina", "wd1", "illumina-careers", "Illumina"),
    ("phinia", "wd5", "PHINIA_Careers", "PHINIA"), ("sprinklr", "wd1", "careers", "Sprinklr"),
    ("trekbikes", "wd1", "TREK", "Trek"), ("lytx", "wd1", "Lytx", "Lytx"),
    ("mimecast", "wd5", "Mimecast-Careers", "Mimecast"), ("sglottery", "wd5", "ScientificGamesExternalCareers", "Sglottery"),
    ("trellix", "wd1", "EnterpriseCareers", "Trellix"), ("syniverse", "wd1", "SyniverseCareers", "Syniverse"),
    ("ansira", "wd1", "Ansira_Careers", "Ansira"), ("plugpower", "wd5", "Plug_Power_Inc", "Plugpower"),
    ("bb", "wd3", "QNX", "Bb"), ("philips", "wd3", "jobs-and-careers", "Philips"),
    ("gsknch", "wd3", "GSKCareers", "Gsknch"), ("rocket", "wd5", "rocket_careers", "Rocket"),
    ("ouryahoo", "wd5", "careers", "Ouryahoo"), ("lnw", "wd5", "SciPlayExternalCareersSite", "Lnw"),
    ("adtran", "wd3", "ADTRAN", "Adtran"), ("comscore", "wd5", "External", "Comscore"),
    ("tencent", "wd1", "Tencent_Careers", "Tencent"), ("autodesk", "wd1", "Ext", "Autodesk"),
    ("wk", "wd3", "External", "Wk"), ("thales", "wd3", "Careers", "Thales"),
    ("cerence", "wd5", "Cerence", "Cerence"),
]


# ── Oracle Recruiting Cloud tenants: (host, site_number, display) ──────────────
# Banks/finance on Oracle ORC (verified India roles incl. equity research, FP&A,
# valuation control). One connector, public JSON, keyword=India.
ORACLE = [
    ("fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com", "CX_2",    "EXL"),        # ~147 India analysts
    ("jpmc.fa.oraclecloud.com",                    "CX_1001", "JPMorgan"),   # FP&A, Valuation Controller (Mumbai)
    ("hdid.fa.us2.oraclecloud.com",                "CX_1",    "Jefferies"),  # Equity Research Associate (Mumbai)
]


# ── SmartRecruiters companies: (company_id, display) ──────────────────────────
SMARTRECRUITERS = [
    ("WNSGlobalServices144", "WNS"),         # credit/market-research analysts, India
    ("NielsenIQ",            "NielsenIQ"),    # Analyst-Banking, data science, India
    # Batch 2 — mined from OpenJobs dataset, live-verified via the public
    # postings API with country=in (2026-07-15; India posting counts in comments).
    # 36 companies, ~2,323 India postings at verification time.
    ("boschgroup", "Bosch Group"), ("Nagarro1", "Nagarro"),                    # 539, 469
    ("ASSYSTEM", "Assystem"), ("renesaselectronics", "Renesas Electronics"),   # 166, 124
    ("miratech1", "Miratech"), ("Ramboll3", "Ramboll"),                        # 122, 117
    ("continental", "Continental"), ("MattelInc", "Mattel"),                   # 104, 78
    ("SikaAG", "Sika Group"), ("Experian", "Experian"),                        # 70, 63
    ("konecranes", "Konecranes"), ("freshworks", "Freshworks"),                # 44, 42
    ("Version1", "Version 1"), ("linkedin3", "LinkedIn"),                      # 42, 41
    ("aristanetworks", "Arista Networks"), ("AFRY", "AFRY"),                   # 34, 34
    ("endava", "Endava"), ("SyngentaGroup", "Syngenta Group"),                 # 34, 33
    ("servicenow", "ServiceNow"), ("vizexperts", "Viz Experts"),               # 29, 19
    ("blend360", "Blend 360"), ("ewargames", "Ewar Games"),                    # 13, 10
    ("gloify", "Gloify"), ("talentfolks", "Talent Folks"),                     # 9, 9
    ("BetaCraftTechnologies", "BetaCraft"), ("TechnorizenSoftwareSolution", "Technorizen"),  # 9, 9
    ("MovingWallsIndiaPvtLtd", "Moving Walls India"), ("InformaGroupPlc", "Informa Group"),  # 8, 8
    ("believe", "Believe"), ("veremark", "Veremark"),                          # 6, 6
    ("springernature", "Springer Nature"), ("Recruitrix", "Recruitrix"),       # 6, 6
    ("KnackStudios", "Knack Studios"), ("WesternDigital", "Western Digital"),  # 5, 5
    ("teampumpkin", "Team Pumpkin"), ("hackerrank", "HackerRank"),             # 5, 5
]


# ── Recruitee companies (slug, display) — mined + verified from OpenJobs ──
RECRUITEE = [
    ("hiddencity", "Hiddencity"), ("immersionspzoo", "Immersionspzoo"), ("reflectorentertainment", "Reflectorentertainment"), ("apply", "Apply"),
    ("infeedo", "Infeedo"), ("mitsogo", "Mitsogo"), ("chaos", "Chaos"), ("futureworks", "Futureworks"),
    ("spocket", "Spocket"), ("framestore", "Framestore"), ("trackman", "Trackman"), ("megaparticleinc", "Megaparticleinc"),
    ("focushomeinteractive", "Focushomeinteractive"), ("realitygames", "Realitygames"), ("playtestcloud", "Playtestcloud"), ("edelman", "Edelman"),
    ("atlys", "Atlys"), ("tgs", "Tgs"), ("gamesglobal", "Gamesglobal"), ("gainpro", "Gainpro"),
    ("saaslabs", "Saaslabs"), ("nxtlvl", "Nxtlvl"), ("villagetalkies", "Villagetalkies"), ("rocketwerkz", "Rocketwerkz"),
    ("terra", "Terra"), ("bettercollective", "Bettercollective"), ("focusentertainment", "Focusentertainment"), ("crazygames", "Crazygames"),
    ("propel", "Propel"), ("curvgroup", "Curvgroup"), ("noobz", "Noobz"), ("exigent", "Exigent"),
    ("csgoroll", "Csgoroll"), ("company3", "Company3"), ("grid", "Grid"), ("pixelpool", "Pixelpool"),
    ("tensquaregames", "Tensquaregames"), ("clever", "Clever"), ("chimpworks", "Chimpworks"), ("lucidgames", "Lucidgames"),
    ("squeezestudio", "Squeezestudio"), ("myr", "Myr"), ("universegroup", "Universegroup"), ("lucidrealitylabs", "Lucidrealitylabs"),
    ("sense", "Sense"), ("rubygamestudio", "Rubygamestudio"), ("playsoncareers", "Playsoncareers"), ("wonderkind", "Wonderkind"),
    ("scorewarrior", "Scorewarrior"), ("stealthstartup", "Stealthstartup"), ("illuvium", "Illuvium"), ("huuuge", "Huuuge"),
    ("vibes", "Vibes"), ("mangopay", "Mangopay"), ("11bitstudios", "11Bitstudios"),
]

# ── Workable companies (slug, display) — public widget API, verified live ─────
# Slug = apply.workable.com/<slug> (the account name in the widget API URL).
# Curated is UNIONed with data/workable_companies.json (harvester) at runtime.
WORKABLE = [
    ("groundtruth", "GroundTruth"),        # verified 2026-07-15, 16 jobs (8 India)
    # From the ATS detector, live-verified 2026-07-16:
    ("apna", "Apna"),                      # 111 jobs
    ("tiger-analytics", "Tiger Analytics"),# 207 jobs
]

# ── BambooHR companies (slug, display) — public careers JSON, verified live ───
# Slug = <slug>.bamboohr.com. Curated UNIONed with data/bamboohr_companies.json.
BAMBOOHR = [
    ("issgh", "Inchcape Shipping Services"),  # verified 2026-07-15, 30 jobs (9 India-ish)
]

# ── Phenom career sites (host, locale_path, display) — public /widgets JSON ───
# Each host verified to return India jobs via POST /widgets (India hit counts
# noted). locale_path is REQUIRED for job deep links: {host}{locale}/job/{seq}
# server-renders the job, while bare /job/{seq} serves the SPA shell that
# bounces to the homepage (found the hard way, 2026-07-16). Verify a tenant's
# locale by GET {host}{locale}/job/{jobSeqNo} and checking the title is in the
# HTML. Some Phenom tenants 403 datacenter IPs — only verified-open hosts here.
PHENOM = [
    ("careers.services.global.ntt", "/global/en", "NTT"),           # ~1,319 India hits
    ("careers.mastercard.com",      "/us/en",     "Mastercard"),    # ~241
    ("careers.dupont.com",          "/us/en",     "DuPont"),        # ~20
    ("jobs.danaher.com",            "/global/en", "Danaher"),       # ~98
    # Batch 2 (2026-07-15 sweep of ~79 enterprise hosts; only open tenants kept)
    ("jobs.thermofisher.com",       "/global/en", "Thermo Fisher"), # ~334
    ("jobs.gsk.com",                "/us/en",     "GSK"),           # ~134
    ("careers.geaerospace.com",     "/global/en", "GE Aerospace"),  # ~14
]

# ── Eightfold tenants (tenant, company-domain, display) — BEST-EFFORT ─────────
# Public API 403s datacenter IPs (verified 2026-07-15); failsafe → contributes
# only if unblocked. Delist if /health shows 0 for a month.
EIGHTFOLD = [
    ("paypal",  "paypal.com",  "PayPal"),
    ("juniper", "juniper.net", "Juniper Networks"),
]

# ── SuccessFactors CSB sites (host, display) — shared server-rendered template ─
# The Indian IT majors nothing else reaches. Verified 2026-07-16 (rows/page in
# comments). HCLTech/Wipro/Chargebee run CUSTOMIZED client-rendered templates →
# 0 rows → deliberately not listed (prove-or-kill).
SFCSB = [
    ("jobs.birlasoft.com",       "Birlasoft"),      # 25/page
    ("careers.capgemini.com",    "Capgemini"),      # 25/page
    ("jobs.sap.com",             "SAP"),            # 25/page
    ("careers.asianpaints.com",  "Asian Paints"),   # 25/page
    ("careers.tatamotors.com",   "Tata Motors"),    # 25/page
    ("jobs.ltts.com",            "LTTS"),           # 9+
    ("careers.ltimindtree.com",  "LTIMindtree"),    # partial, paginates
]

# ── Kula companies (slug, display) — careers.kula.ai/{slug}, RSC-payload parse ─
# India startups on Kula ATS (found via the ATS detector). Verify a slug by
# checking careers.kula.ai/{slug} renders an "Open Positions" list.
KULA = [
    ("cashfree", "Cashfree Payments"),  # verified 2026-07-16, 51 jobs
    ("plumhq", "Plum"),                 # 54 jobs
    ("clevertap", "CleverTap"),         # 17 jobs
]

# ── Harvested lists (our own, from ingest/harvester.py via Common Crawl) ───────
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
# Cap how many harvested boards the daily run uses (sorted by job count), so the
# run stays bounded even as the harvested file grows to thousands. The full file
# is still kept; raise this as the scaling architecture matures.
_MAX_HARVESTED = int(os.environ.get("MAX_HARVESTED_PER_ATS", "1000"))


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
def all_workable():   return _merge(WORKABLE, _harvested("workable"))
def all_bamboohr():   return _merge(BAMBOOHR, _harvested("bamboohr"))


def _harvested_workday():
    """Harvested Workday tenants → [(tenant, wd, site, display)], capped.

    Workday identity is a (tenant, wd_number, site) TRIPLE, so its harvested
    file is a dict {tenant: {"wd": "wd5", "site": "...", "count": N}} rather
    than the flat {slug: count} the other ATSes use.
    """
    path = os.path.join(_DATA_DIR, "workday_companies.json")
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        return []
    items = sorted(d.items(), key=lambda kv: kv[1].get("count", 0), reverse=True)
    return [(t, v["wd"], v["site"], t) for t, v in items[:_MAX_HARVESTED]
            if v.get("wd") and v.get("site")]


def all_workday():
    """Curated WORKDAY unioned with harvested tenants (deduped by tenant).

    Harvested tenants are OFF by default (WORKDAY_INCLUDE_HARVESTED=1 enables).
    Rationale: workday.SEARCH_TEXT="India" is a loose ranker, not a filter — a
    US-only tenant still returns its jobs, so ~190 harvested tenants add ~25k+
    mostly-non-India rows/run. Flip on AFTER the jobs/user_job_matches
    normalization lands (see ROADMAP "NOW").
    """
    if os.environ.get("WORKDAY_INCLUDE_HARVESTED", "0").lower() not in ("1", "true", "yes"):
        return list(WORKDAY)
    seen = {t for t, _, _, _ in WORKDAY}
    out = list(WORKDAY)
    for t, wd, site, disp in _harvested_workday():
        if t not in seen:
            out.append((t, wd, site, disp))
            seen.add(t)
    return out


# ── Domain tagging (finance vs tech vs general) ────────────────────────────────
# Used to (a) prioritise fetching the sources a night's active users need, and
# (b) give the matcher a provenance signal (a finance job from a finance-GCC
# board outranks a keyword-only match). Coarse on purpose — finance + tech are
# the two markets this product serves; everything else is "general".

# Workday tenants that are finance/banking GCCs (the curated finance block).
_FINANCE_WD = {
    "statestreet","db","lseg","wf","ntrs","morningstar","blackrock","nasdaq","spgi",
    "barclays","synchronyfinancial","broadridge","fiserv","fmr","capitalone","fis",
    "citi","ms","ghr","factset","visa","mastercard","pwc",
}

# SmartRecruiters ids that are finance/analytics GCCs (the original curated
# pair + Experian). The OpenJobs batch is engineering/IT-services heavy → tech.
_FINANCE_SR = {"WNSGlobalServices144", "NielsenIQ", "Experian"}


def unit_domain(label: str, uid: str) -> str:
    """Coarse domain for a fetch unit: 'finance' | 'tech' | 'general'."""
    if label == "oracle":
        return "finance"          # ORC registry is all finance GCCs
    if label == "smartrecruiters":
        return "finance" if uid in _FINANCE_SR else "tech"
    if label == "workday":
        return "finance" if uid in _FINANCE_WD else "tech"
    if label in ("workable", "bamboohr"):
        # Curated boards are hand-verified; harvested (in the JSON) → general.
        curated = {s for s, _ in (WORKABLE if label == "workable" else BAMBOOHR)}
        return "tech" if uid in curated else "general"
    if label == "phenom":
        # uid is the host (first tuple element)
        return "finance" if uid == "careers.mastercard.com" else "tech"
    if label == "eightfold":
        return "tech"
    if label == "kula":
        return "tech"             # India-startup ATS (fintech/SaaS)
    if label == "successfactors":
        return "tech"             # Indian IT majors + enterprise
    if label in ("greenhouse", "lever", "ashby"):
        # Curated boards are hand-picked tech companies; harvested (in the JSON
        # files) are unknown → general.
        curated = {s for s, _ in (GREENHOUSE if label == "greenhouse"
                                   else LEVER if label == "lever" else ASHBY)}
        return "tech" if uid in curated else "general"
    if label == "instahyre":
        return "tech"             # India tech/analytics board
    if label in ("recruitee", "foundit"):
        return "general"
    return "general"              # jobspy, aggregators
