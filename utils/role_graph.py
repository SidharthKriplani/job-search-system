"""
Role-family graph + sector layer  (the relevance "neighbourhood" engine)
------------------------------------------------------------------------
A target role isn't a point — it's a NEIGHBOURHOOD. "Data Scientist" should also
surface ML Engineer, Data Engineer, Analyst, etc., each at a different closeness.
This module is the curated source of truth for that graph, plus a SECTOR keyword
layer for domain search ("jobs in finance/fintech").

Design choices (per product decisions):
  • Curated graph (transparent + doubles as the future competence map). Embeddings
    can boost later; LLM expansion later still.
  • Field-dependent: tech families lean on the title graph (titles standardised);
    finance families also carry a SECTOR so non-standard finance titles still match.
  • Auto-expand with DECAY: target = 1.0, neighbours < 1.0, so exact matches rank
    highest and adjacency never outranks the real thing.

Public API:
  expand_roles(roles)            -> {canonical_role: weight}   (1.0 == the target)
  sectors_for(roles, industries) -> set[str]                   (sector names)
  sector_keywords(sectors)       -> set[str]                   (keywords to match)
"""
import re
from typing import Dict, List, Set, Iterable

# ── Sector keyword sets (domain layer) ───────────────────────────────────────
SECTORS: Dict[str, Set[str]] = {
    "finance": {
        "finance", "financial", "bank", "banking", "capital", "equity", "equities",
        "securities", "investment", "investing", "investor", "fund", "funds",
        "asset management", "wealth", "hedge", "private equity", "venture capital",
        "merger", "acquisition", "m&a", "credit", "lending", "loan", "mortgage",
        "treasury", "brokerage", "broker", "trading", "trader", "underwriting",
        "valuation", "portfolio", "ipo", "debt", "fixed income", "derivatives",
        "actuarial", "audit", "taxation", "accounting", "fund accounting",
    },
    "fintech": {
        "fintech", "payments", "payment", "neobank", "lending", "upi", "wallet",
        "bnpl", "remittance", "card", "cards", "merchant", "kyc", "ledger",
        "razorpay", "paytm", "phonepe", "cred", "stripe", "billing", "payouts",
    },
    "healthcare": {
        "healthcare", "health", "hospital", "clinical", "pharma", "pharmaceutical",
        "biotech", "medical", "patient", "diagnostics", "healthtech", "life sciences",
    },
    "ecommerce": {
        "ecommerce", "e-commerce", "retail", "marketplace", "d2c", "consumer",
        "logistics", "supply chain", "fulfilment", "fulfillment", "quick commerce",
    },
    "tech": {
        "software", "saas", "cloud", "platform", "infrastructure", "developer",
        "api", "devtools", "b2b software", "enterprise software",
    },
}

# How a free-text "industry" the user typed maps onto a sector.
_INDUSTRY_TO_SECTOR = {
    "finance": "finance", "financial": "finance", "fin": "finance", "bfsi": "finance",
    "banking": "finance", "investment": "finance", "investments": "finance",
    "ib": "finance", "investment banking": "finance", "capital markets": "finance",
    "fintech": "fintech", "payments": "fintech",
    "healthcare": "healthcare", "health": "healthcare", "pharma": "healthcare",
    "biotech": "healthcare", "healthtech": "healthcare",
    "ecommerce": "ecommerce", "e-commerce": "ecommerce", "retail": "ecommerce",
    "consumer": "ecommerce", "d2c": "ecommerce",
    "tech": "tech", "saas": "tech", "software": "tech", "it": "tech",
}

# ── Role families ────────────────────────────────────────────────────────────
# Each family: a sector tag (or None), a default intra-family closeness, the set
# of member roles, and a few STRONG edges that override the default. Edges are
# treated as symmetric. Anything not in a family still works (weight 1.0, handled
# by the caller's fallback).
_DEFAULT_W = 0.55

_FAMILIES = {
    "data_ml": {
        "sector": "tech",
        "default": 0.6,
        "members": [
            "data scientist", "machine learning engineer", "ai engineer",
            "data engineer", "data analyst", "analytics engineer",
            "applied scientist", "research scientist", "decision scientist",
            "mlops engineer", "business intelligence analyst", "product analyst",
            "business analyst", "data science manager", "nlp engineer",
            "computer vision engineer", "recommendation systems engineer",
        ],
        "strong": [
            ("data scientist", "machine learning engineer", 0.9),
            ("machine learning engineer", "ai engineer", 0.92),
            ("data scientist", "applied scientist", 0.85),
            ("data scientist", "decision scientist", 0.82),
            ("data scientist", "data analyst", 0.75),
            ("machine learning engineer", "mlops engineer", 0.8),
            ("machine learning engineer", "nlp engineer", 0.8),
            ("machine learning engineer", "computer vision engineer", 0.8),
            ("machine learning engineer", "recommendation systems engineer", 0.78),
            ("data analyst", "business intelligence analyst", 0.85),
            ("data analyst", "business analyst", 0.7),
            ("data analyst", "product analyst", 0.75),
            ("data engineer", "analytics engineer", 0.82),
            ("data scientist", "data science manager", 0.7),
        ],
    },
    "software": {
        "sector": "tech",
        "default": 0.6,
        "members": [
            "software engineer", "backend engineer", "frontend engineer",
            "full stack engineer", "devops engineer", "site reliability engineer",
            "platform engineer", "mobile engineer", "cloud engineer",
            "security engineer", "qa engineer",
        ],
        "strong": [
            ("software engineer", "backend engineer", 0.9),
            ("software engineer", "full stack engineer", 0.9),
            ("software engineer", "frontend engineer", 0.8),
            ("backend engineer", "platform engineer", 0.8),
            ("devops engineer", "site reliability engineer", 0.9),
            ("devops engineer", "cloud engineer", 0.82),
        ],
    },
    "product": {
        "sector": None,
        "default": 0.5,
        "members": [
            "product manager", "product owner", "program manager",
            "technical program manager", "product analyst", "associate product manager",
            "group product manager",
        ],
        "strong": [
            ("product manager", "product owner", 0.85),
            ("product manager", "associate product manager", 0.85),
            ("product manager", "group product manager", 0.8),
            ("product manager", "program manager", 0.6),
            ("product manager", "product analyst", 0.6),
        ],
    },
    "design": {
        "sector": None,
        "default": 0.55,
        "members": [
            "product designer", "ux designer", "ui designer", "ux researcher",
            "interaction designer", "visual designer", "design lead",
        ],
        "strong": [
            ("product designer", "ux designer", 0.9),
            ("ux designer", "ui designer", 0.85),
            ("product designer", "ux researcher", 0.7),
        ],
    },
    # FINANCE — dense + alias-heavy; carries the finance sector so non-standard
    # titles still get caught by the keyword layer.
    "finance_ib": {
        "sector": "finance",
        "default": 0.55,
        "members": [
            "investment banker", "investment banking analyst", "investment banking associate",
            "mergers and acquisitions", "private equity associate", "venture capital analyst",
            "equity research analyst", "credit analyst", "corporate development",
            "leveraged finance", "capital markets", "debt capital markets",
            "equity capital markets", "restructuring", "valuations analyst",
            "financial analyst", "fp&a analyst", "asset management", "portfolio manager",
            "hedge fund analyst", "quantitative analyst", "risk analyst",
            "transaction advisory", "private credit", "treasury analyst",
            "investment associate", "fund manager",
        ],
        "strong": [
            ("investment banker", "investment banking analyst", 0.95),
            ("investment banker", "investment banking associate", 0.95),
            ("investment banker", "mergers and acquisitions", 0.9),
            ("investment banker", "leveraged finance", 0.85),
            ("investment banker", "capital markets", 0.82),
            ("investment banker", "equity capital markets", 0.82),
            ("investment banker", "debt capital markets", 0.8),
            ("investment banker", "restructuring", 0.8),
            ("investment banker", "private equity associate", 0.82),
            ("investment banker", "corporate development", 0.8),
            ("investment banker", "equity research analyst", 0.75),
            ("investment banker", "transaction advisory", 0.78),
            ("private equity associate", "venture capital analyst", 0.8),
            ("private equity associate", "investment associate", 0.85),
            ("financial analyst", "fp&a analyst", 0.85),
            ("asset management", "portfolio manager", 0.85),
            ("asset management", "fund manager", 0.82),
            ("quantitative analyst", "risk analyst", 0.7),
        ],
    },
    "marketing": {
        "sector": None,
        "default": 0.5,
        "members": [
            "marketing manager", "growth manager", "performance marketing",
            "digital marketing", "content marketing", "brand manager",
            "product marketing manager", "seo specialist",
        ],
        "strong": [
            ("marketing manager", "brand manager", 0.8),
            ("marketing manager", "digital marketing", 0.8),
            ("growth manager", "performance marketing", 0.85),
            ("marketing manager", "product marketing manager", 0.7),
        ],
    },
    "sales": {
        "sector": None,
        "default": 0.5,
        "members": [
            "sales manager", "account executive", "business development manager",
            "account manager", "sales development representative", "inside sales",
            "key account manager",
        ],
        "strong": [
            ("account executive", "business development manager", 0.8),
            ("account executive", "account manager", 0.78),
            ("sales manager", "key account manager", 0.75),
        ],
    },
    "consulting": {
        "sector": None,
        "default": 0.55,
        "members": [
            "management consultant", "strategy consultant", "business consultant",
            "associate consultant", "strategy analyst", "business analyst",
        ],
        "strong": [
            ("management consultant", "strategy consultant", 0.9),
            ("strategy consultant", "strategy analyst", 0.75),
        ],
    },
}

# Aliases: free-text the user might type → a canonical member above.
_ALIASES = {
    "data science": "data scientist", "ds": "data scientist",
    "ml": "machine learning engineer", "ml engineer": "machine learning engineer",
    "machine learning": "machine learning engineer",
    "ai": "ai engineer", "artificial intelligence": "ai engineer",
    "mle": "machine learning engineer", "mlops": "mlops engineer",
    "nlp": "nlp engineer", "cv": "computer vision engineer",
    "recsys": "recommendation systems engineer",
    "ba": "business analyst", "bi": "business intelligence analyst",
    "swe": "software engineer", "sde": "software engineer",
    "backend": "backend engineer", "frontend": "frontend engineer",
    "fullstack": "full stack engineer", "full-stack": "full stack engineer",
    "sre": "site reliability engineer", "devops": "devops engineer",
    "pm": "product manager", "apm": "associate product manager",
    "tpm": "technical program manager", "gpm": "group product manager",
    "ux": "ux designer", "ui": "ui designer",
    "ib": "investment banker", "investment banking": "investment banker",
    "m&a": "mergers and acquisitions", "mna": "mergers and acquisitions",
    "pe": "private equity associate", "vc": "venture capital analyst",
    "er": "equity research analyst", "equity research": "equity research analyst",
    "fpa": "fp&a analyst", "fp&a": "fp&a analyst",
    "quant": "quantitative analyst", "pms": "portfolio manager",
}

# Reverse index: member role -> family key (built once).
_MEMBER_TO_FAMILY: Dict[str, str] = {}
for _fam, _spec in _FAMILIES.items():
    for _m in _spec["members"]:
        _MEMBER_TO_FAMILY.setdefault(_m, _fam)


def normalize_role(role: str) -> str:
    """Lowercase + alias-resolve a free-text role to a canonical member if known."""
    r = (role or "").strip().lower()
    if r in _ALIASES:
        return _ALIASES[r]
    return r


def _edge_weight(fam: str, a: str, b: str) -> float:
    spec = _FAMILIES[fam]
    for x, y, w in spec.get("strong", []):
        if {x, y} == {a, b}:
            return w
    return spec.get("default", _DEFAULT_W)


def expand_roles(roles: Iterable[str]) -> Dict[str, float]:
    """Expand target roles into a weighted neighbourhood. Target = 1.0; neighbours
    decay by edge weight. Unknown roles map to themselves at 1.0 (caller falls back
    to plain matching for those)."""
    out: Dict[str, float] = {}
    for raw in roles or []:
        canon = normalize_role(raw)
        out[canon] = max(out.get(canon, 0.0), 1.0)
        fam = _MEMBER_TO_FAMILY.get(canon)
        if not fam:
            continue
        for member in _FAMILIES[fam]["members"]:
            if member == canon:
                continue
            w = _edge_weight(fam, canon, member)
            out[member] = max(out.get(member, 0.0), w)
    return out


# Sectors whose TITLES are non-standard enough that we auto-activate the keyword
# net from a role alone (finance is the motivating case). "tech" is deliberately
# excluded — tech titles are standardised, so the title graph carries it and we
# don't want to impose a keyword requirement that under-scores tech jobs.
_AUTO_SECTORS = {"finance", "fintech", "healthcare", "ecommerce"}

def sectors_for(roles: Iterable[str], industries: Iterable[str]) -> Set[str]:
    """Sectors implied by (a) explicitly-set industries — always honoured — and
    (b) the target roles' families, but only for non-standard-title sectors
    (finance, etc.), so an investment-banker target turns on the finance net while
    a data-scientist target doesn't impose a 'tech' keyword requirement."""
    found: Set[str] = set()
    for ind in industries or []:
        key = (ind or "").strip().lower()
        if key in _INDUSTRY_TO_SECTOR:
            found.add(_INDUSTRY_TO_SECTOR[key])
        elif key in SECTORS:
            found.add(key)
    for raw in roles or []:
        fam = _MEMBER_TO_FAMILY.get(normalize_role(raw))
        sec = _FAMILIES[fam].get("sector") if fam else None
        if sec and sec in _AUTO_SECTORS:
            found.add(sec)
    return found


def sector_keywords(sectors: Iterable[str]) -> Set[str]:
    kw: Set[str] = set()
    for s in sectors or []:
        kw |= SECTORS.get(s, set())
    return kw


def roles_from_text(text: str, limit: int = 6) -> List[str]:
    """Detect canonical roles mentioned in free text (a résumé) — full member
    phrases (precise) + whole-word aliases, ranked by hit strength. Lets the
    résumé seed/drive the search. Mirror of `rolesFromText` in roleGraph.ts."""
    low = " " + re.sub(r"\s+", " ", re.sub(r"[^a-z0-9&+ ]", " ", (text or "").lower())) + " "
    score: Dict[str, int] = {}
    for member in _MEMBER_TO_FAMILY:
        if f" {member} " in low:
            score[member] = score.get(member, 0) + 3
    for alias, canon in _ALIASES.items():
        if f" {alias} " in low:
            score[canon] = score.get(canon, 0) + 2
    return [r for r, _ in sorted(score.items(), key=lambda x: -x[1])][:limit]
