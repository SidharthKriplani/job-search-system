"""
Facet normalisation — messy raw job fields → clean, filterable buckets.

Job titles and locations from external boards are chaos ("Sr. SWE II",
"Bengaluru-VTP, India", "Mumbai-Lower Parel"). To offer a Position and Location
filter that isn't a wall of near-duplicate noise, we map each job to ONE
canonical bucket at write time and store it (job_feed.position / .location_city).
All the fuzzy naming-approximation logic lives HERE, in one place.

Deliberately coarse: the goal is a usable dropdown, not a taxonomy. Anything
unrecognised falls to "Other" (positions) or the raw first city / "Other".
"""
from typing import Optional

# ── Position buckets ──────────────────────────────────────────────────────────
# Ordered: MOST specific first (a title hits the first bucket whose keywords all
# appear). Keep phrases multi-word where ambiguity is high ("data analyst" before
# bare "analyst"). Finance + tech are first-class; common cross-industry roles too.
_POSITION_RULES = [
    ("Machine Learning Engineer", ("machine learning", "ml engineer", "mlops", "deep learning")),
    ("Data Scientist",            ("data scientist", "data science", "applied scientist", "research scientist")),
    ("Data Engineer",             ("data engineer", "analytics engineer", "etl", "data platform")),
    ("Data Analyst",              ("data analyst", "analytics analyst", "insights analyst")),
    ("Business Analyst",          ("business analyst", "business intelligence", " bi analyst")),
    ("Product Analyst",           ("product analyst",)),
    ("Product Manager",           ("product manager", "product management", " pm ", "group product")),
    ("Equity Research Analyst",   ("equity research", "research analyst", "investment research", "credit research")),
    ("Investment Banking",        ("investment bank", "m&a", "mergers", " ib ", "capital markets")),
    ("Risk / Credit Analyst",     ("risk analyst", "credit risk", "credit analyst", "market risk", "kyc", "aml")),
    ("Financial Analyst / FP&A",  ("financial analyst", "fp&a", "fpa", "valuation", "financial planning")),
    ("Accountant",                ("accountant", "accounting", "fund accountant", "controller")),
    ("Quant",                     ("quant", "quantitative")),
    ("Consultant",                ("consultant", "consulting", "advisory")),
    ("DevOps / SRE",              ("devops", "site reliability", " sre", "platform engineer", "infrastructure engineer")),
    ("Frontend Engineer",         ("frontend", "front end", "front-end", "react developer", "ui engineer")),
    ("Backend Engineer",          ("backend", "back end", "back-end", "server engineer")),
    ("Full-Stack Engineer",       ("full stack", "full-stack", "fullstack")),
    ("Mobile Engineer",           ("android", "ios engineer", "mobile engineer", "flutter")),
    ("Software Engineer",         ("software engineer", "software developer", "sde", "swe", "developer", "programmer")),
    ("Designer",                  ("designer", "ux", "ui/ux", "product design")),
    ("Sales",                     ("sales", "account executive", "business development", "bdr", "sdr")),
    ("Marketing",                 ("marketing", "growth", "seo", "content", "brand")),
    ("Operations",                ("operations", "ops ", "program manager", "project manager")),
    ("Analyst (general)",         ("analyst",)),
    ("Engineer (general)",        ("engineer",)),
    ("Internship",                ("intern", "internship", "trainee")),
]


def normalize_position(title: Optional[str]) -> str:
    t = f" {(title or '').lower()} "
    if not t.strip():
        return "Other"
    for label, kws in _POSITION_RULES:
        if any(k in t for k in kws):
            return label
    return "Other"


# ── Location buckets ──────────────────────────────────────────────────────────
_REMOTE = ("remote", "wfh", "work from home", "anywhere")
# alias fragment → canonical city
_CITY_ALIASES = [
    (("bengaluru", "bangalore", "bangaluru", "blr"), "Bangalore"),
    (("mumbai", "bombay", "navi mumbai"),            "Mumbai"),
    (("gurgaon", "gurugram"),                        "Gurugram"),
    (("noida", "greater noida"),                     "Noida"),
    (("new delhi", "delhi"),                         "Delhi"),
    (("hyderabad", "hyd", "secunderabad"),           "Hyderabad"),
    (("pune",),                                      "Pune"),
    (("chennai", "madras"),                          "Chennai"),
    (("kolkata", "calcutta"),                        "Kolkata"),
    (("ahmedabad", "gandhinagar", "gift city"),      "Ahmedabad / GIFT"),
    (("jaipur",),                                    "Jaipur"),
    (("kochi", "cochin", "trivandrum", "thiruvananthapuram"), "Kerala"),
    (("chandigarh", "mohali"),                       "Chandigarh"),
    (("indore",),                                    "Indore"),
    (("coimbatore",),                                "Coimbatore"),
]
_FOREIGN = (
    " usa", " u.s", "united states", " uk", "united kingdom", "london", "england",
    "germany", "france", "canada", "singapore", "dubai", "uae", "australia",
    "netherlands", "ireland", "poland", "spain", "mexico", "brazil", "china",
    "japan", "philippines", "malaysia", "san francisco", "new york", "seattle",
    "austin", "berlin", "amsterdam", "toronto", "sydney", "europe",
)


def normalize_location(location: Optional[str]) -> str:
    loc = (location or "").lower().strip()
    if not loc:
        return "Unspecified"
    if any(k in loc for k in _REMOTE):
        return "Remote"
    for fragments, city in _CITY_ALIASES:
        if any(f in loc for f in fragments):
            return city
    if "india" in loc:
        return "India (other)"
    if any(f in loc for f in _FOREIGN):
        return "Overseas"
    return "Other"
