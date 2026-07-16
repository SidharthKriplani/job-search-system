"""
Company-name normalization — one canonical name per employer, applied at
ingestion (make_job) so every connector benefits and dedup keys line up.

Two layers:
  1. Mechanical cleanup — strip legal suffixes ("Pvt Ltd", "Private Limited",
     "Inc.", "LLC", …), collapse whitespace, trim stray punctuation.
  2. Alias map (data/company_aliases.json) — hand-curated {alias: canonical}
     for the cases mechanics can't fix ("BoschGroup" → "Bosch Group",
     "Cashfree Payments India" → "Cashfree Payments"). Keys matched
     case-insensitively AFTER mechanical cleanup. EXTEND FREELY.

Only display names change; source_job_id-based dedup is unaffected.
"""
import json
import os
import re
from functools import lru_cache

_DATA = os.path.join(os.path.dirname(__file__), "data")

# Trailing legal / corporate suffixes. Applied repeatedly (handles
# "X Technologies Pvt. Ltd." → "X Technologies"). A separator (space/comma/dot)
# is REQUIRED before the suffix so brands merely ENDING in these letters
# ("Cisco", "Adani Ltd" vs "Unacademy") aren't clipped mid-word. "India" is
# deliberately NOT stripped ("Air India") — handle those via the alias map.
_SUFFIXES = re.compile(
    r"(?:[\s,.]+)(?:"
    r"private\s+limited|pvt\.?\s*ltd\.?|pte\.?\s*ltd\.?|ltd\.?|limited|"
    r"inc\.?|incorporated|llc|llp|corp\.?|corporation|co\.?|gmbh|s\.?a\.?|plc"
    r")\s*$",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _aliases() -> dict:
    path = os.path.join(_DATA, "company_aliases.json")
    try:
        with open(path) as f:
            return {k.lower(): v for k, v in json.load(f).items()}
    except Exception:
        return {}


def canonical_company(name: str) -> str:
    """Best-effort canonical employer name. Never raises; '' stays ''."""
    if not name:
        return ""
    s = re.sub(r"\s+", " ", str(name)).strip(" ,.-·|")
    # peel suffixes (max a few rounds; "India Private Limited" needs two)
    for _ in range(3):
        s2 = _SUFFIXES.sub("", s).strip(" ,.-")
        if s2 == s or not s2:
            break
        s = s2
    hit = _aliases().get(s.lower())
    return hit if hit else s
