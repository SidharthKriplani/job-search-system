"""
Feedback-driven tuning — the loop that makes feed_feedback actually change
ranking (ROADMAP "Act on the feedback loop").

Two layers, both failsafe (missing files / bad data → no-op):

1. GLOBAL overrides (ingest/data/tuning_overrides.json) — score multipliers
   curated from weekly TUNING_REPORT.md evidence. scripts/feedback_report.py
   writes SUGGESTIONS (tuning_suggestions.json); a human/agent promotes
   entries into tuning_overrides.json — deliberate two-step so the matcher
   never auto-mutates from a handful of angry taps.

     {"demote_title_terms": {"telecaller": 0.5},   # term in title → ×0.5
      "demote_companies":   {"staffing xyz": 0.6}, # company match → ×0.6
      "boost_companies":    {}}                    # ×>1 allowed, capped 1.2

2. PER-USER affinity — computed per matching run from the flags already on
   the user's stored rows (is_saved / is_applied / is_dismissed):
     - company with a saved/applied job        → small boost (×1.05)
     - company dismissed ≥2 times              → demote (×0.9)
   Bounded multipliers: tuning nudges rank, it never flips a Strong fit to
   a Possible on its own.
"""
import json
import logging
import os
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_OVERRIDES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "ingest", "data", "tuning_overrides.json")

_MIN_MULT, _MAX_MULT = 0.5, 1.2   # hard bounds on any combined adjustment


@lru_cache(maxsize=1)
def _overrides() -> Dict:
    try:
        with open(_OVERRIDES_PATH) as f:
            d = json.load(f)
        return {
            "demote_title_terms": {str(k).lower(): float(v) for k, v in (d.get("demote_title_terms") or {}).items()},
            "demote_companies":   {str(k).lower(): float(v) for k, v in (d.get("demote_companies") or {}).items()},
            "boost_companies":    {str(k).lower(): float(v) for k, v in (d.get("boost_companies") or {}).items()},
        }
    except Exception:
        return {"demote_title_terms": {}, "demote_companies": {}, "boost_companies": {}}


def collect_affinity(jobs: List[Dict]) -> Dict:
    """Pre-pass over the candidate set (stored rows carry user flags) →
    {liked_companies: set, disliked_companies: set}. Never raises."""
    liked, dismissed_count = set(), {}
    try:
        for j in jobs:
            co = (j.get("company") or "").lower()
            if not co:
                continue
            if j.get("is_saved") or j.get("is_applied"):
                liked.add(co)
            if j.get("is_dismissed"):
                dismissed_count[co] = dismissed_count.get(co, 0) + 1
        disliked = {c for c, n in dismissed_count.items() if n >= 2 and c not in liked}
        return {"liked": liked, "disliked": disliked}
    except Exception:
        return {"liked": set(), "disliked": set()}


def adjust(score: float, title: str, company: str,
           affinity: Optional[Dict] = None) -> Tuple[float, Optional[str]]:
    """Apply global overrides + per-user affinity. Returns (score, note|None)."""
    try:
        ov = _overrides()
        t, c = (title or "").lower(), (company or "").lower()
        mult, note = 1.0, None

        for term, m in ov["demote_title_terms"].items():
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", t):
                mult *= m
                note = "Tuned down (community feedback)"
                break
        for co, m in ov["demote_companies"].items():
            if co in c:
                mult *= m
                note = note or "Tuned down (community feedback)"
                break
        for co, m in ov["boost_companies"].items():
            if co in c:
                mult *= m
                break

        if affinity:
            if c in affinity.get("liked", ()):
                mult *= 1.05
                note = note or "You've engaged with this company"
            elif c in affinity.get("disliked", ()):
                mult *= 0.9
                note = note or "You've dismissed this company before"

        mult = max(_MIN_MULT, min(_MAX_MULT, mult))
        return (min(score * mult, 1.0), note if mult != 1.0 else None)
    except Exception:
        return (score, None)
