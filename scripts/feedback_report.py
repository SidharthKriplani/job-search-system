"""
Weekly relevance-tuning report — turns feed_feedback rows into actionable
matcher tuning suggestions, written to docs/TUNING_REPORT.md (committed by the
weekly workflow). The loop: users tap "Not relevant → why" → this aggregates →
you (or an AI session) adjust role_graph weights / filters with evidence.

Run: python -m scripts.feedback_report   (needs SUPABASE_URL + SERVICE_KEY)
"""
import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import supabase_client as sb  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("feedback_report")

REASON_HINTS = {
    "wrong_role":      "role-graph over-expansion — check which target roles matched these titles and lower/remove the offending neighbour weight in utils/role_graph.py",
    "wrong_location":  "location filter leak — check India-default and remote handling in utils/filter.py",
    "wrong_seniority": "level_fit too permissive — check role_graph.job_level cues for these titles",
    "wrong_company":   "suggest exclude_companies to the user, or blocklist staffing agencies globally",
    "stale":           "dead-link cleanup gap — check the source's cleanup coverage",
    "other":           "read the raw rows — pattern unknown",
}


def main() -> None:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    client = sb.get_client()
    rows = []
    page, start = 1000, 0
    while True:
        batch = client.table("feed_feedback").select("*") \
            .gte("created_at", since).order("id") \
            .range(start, start + page - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < page:
            break
        start += page

    lines = [
        "# Relevance tuning report",
        "",
        f"_Window: last 7 days · generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        f"**{len(rows)} 'not relevant' signals** from users this week.",
        "",
    ]

    if rows:
        by_reason = Counter(r["reason"] for r in rows)
        lines += ["## By reason", ""]
        for reason, n in by_reason.most_common():
            lines.append(f"- **{reason}** × {n} — {REASON_HINTS.get(reason, '')}")

        by_source = Counter(r.get("source") or "?" for r in rows)
        lines += ["", "## By source", ""]
        for src, n in by_source.most_common(8):
            lines.append(f"- {src}: {n}")

        # Titles most often rejected per reason — the concrete tuning evidence.
        titles = defaultdict(Counter)
        for r in rows:
            titles[r["reason"]][(r.get("job_title") or "?")[:60]] += 1
        lines += ["", "## Most-rejected titles (evidence for role-graph edits)", ""]
        for reason, counter in titles.items():
            top = counter.most_common(5)
            if top:
                lines.append(f"**{reason}:**")
                for t, n in top:
                    lines.append(f"  - {t} × {n}")

        high_score = [r for r in rows if (r.get("match_score") or 0) >= 0.7]
        if high_score:
            lines += ["", f"⚠️ **{len(high_score)} rejections had match_score ≥ 0.7** — "
                          "the scorer was confidently wrong on these; prioritise them.", ""]

        # ── Pattern mining → machine-readable SUGGESTIONS (not auto-applied) ──
        # Recurring title terms in wrong_role/wrong_seniority rejections and
        # recurring companies in wrong_company rejections become candidate
        # overrides. Promote reviewed entries into
        # ingest/data/tuning_overrides.json — utils/tuning.py applies them at
        # scoring time. Two-step by design: evidence → review → live.
        import json as _json
        import re as _re
        STOP = {"and", "the", "for", "with", "of", "in", "a", "to", "senior", "junior",
                "manager", "lead", "engineer", "analyst", "associate", "executive",
                "specialist", "developer", "consultant", "officer", "head", "ii", "iii"}
        term_hits = Counter()
        for r in rows:
            if r.get("reason") in ("wrong_role", "wrong_seniority"):
                for w in _re.findall(r"[a-z][a-z+#/-]{2,}", (r.get("job_title") or "").lower()):
                    if w not in STOP:
                        term_hits[w] += 1
        co_hits = Counter((r.get("company") or "").strip().lower()
                          for r in rows if r.get("reason") == "wrong_company" and r.get("company"))

        suggestions = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_days": 7,
            "demote_title_terms": {t: 0.7 for t, n in term_hits.most_common(15) if n >= 3},
            "demote_companies":   {c: 0.6 for c, n in co_hits.most_common(10) if n >= 3},
            "_promote_to": "ingest/data/tuning_overrides.json (review first)",
        }
        try:
            with open("ingest/data/tuning_suggestions.json", "w") as f:
                _json.dump(suggestions, f, indent=1, sort_keys=True)
        except Exception as e:
            logger.warning(f"could not write suggestions: {e}")

        if suggestions["demote_title_terms"] or suggestions["demote_companies"]:
            lines += ["", "## Suggested overrides (review → promote to tuning_overrides.json)", ""]
            for t, m in suggestions["demote_title_terms"].items():
                lines.append(f"- demote title term `{t}` → ×{m} ({term_hits[t]} rejections)")
            for c, m in suggestions["demote_companies"].items():
                lines.append(f"- demote company `{c}` → ×{m} ({co_hits[c]} rejections)")
    else:
        lines.append("_No feedback this week — either the feed is good or nobody used the button._")

    lines.append("")
    with open("docs/TUNING_REPORT.md", "w") as f:
        f.write("\n".join(lines))
    logger.info(f"Wrote docs/TUNING_REPORT.md ({len(rows)} signals)")


if __name__ == "__main__":
    main()
