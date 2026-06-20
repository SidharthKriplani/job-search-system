"""
Semantic matching via free local embeddings (FastEmbed / ONNX — no API, no torch).

This is the honest "semantic" layer: it understands that "ML Engineer" ≈ "Data
Scientist" and "valuation" ≈ "financial modeling" — things the keyword/stem
matcher can't. It's OPT-IN and fully optional:

  - Disabled unless env USE_EMBEDDINGS is truthy AND fastembed is installed.
  - If unavailable, every caller degrades to keyword/stem scoring (no-op).
  - Model: BAAI/bge-small-en-v1.5 (~130MB, CPU). Override with EMBED_MODEL.

To enable: `pip install -r requirements-embeddings.txt` and set USE_EMBEDDINGS=1.

Design note: we re-rank only the ALREADY keyword-filtered shortlist (small), not
the whole pool — the cheap-filter-then-semantic-rerank two-stage from SCALING.md.
"""
import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_NAME = os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")


def available() -> bool:
    """True only if explicitly enabled AND the library is importable."""
    if os.environ.get("USE_EMBEDDINGS", "").lower() not in ("1", "true", "yes"):
        return False
    try:
        import fastembed  # noqa: F401
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def _model():
    global _MODEL
    if _MODEL is None:
        from fastembed import TextEmbedding
        logger.info(f"[embeddings] loading {_MODEL_NAME}")
        _MODEL = TextEmbedding(model_name=_MODEL_NAME)
    return _MODEL


def rerank(profile_text: str, jobs: List[Dict], blend: float = 0.4) -> List[Dict]:
    """
    Blend semantic similarity (profile_text vs each job's title+JD) into the
    existing keyword match_score, then re-sort. `blend` = weight given to the
    semantic signal (0..1). Mutates and returns `jobs`. No-op on any failure.
    """
    if not jobs or not (profile_text or "").strip():
        return jobs
    try:
        import numpy as np
        job_texts = [f"{j.get('job_title','')} {j.get('description_snippet','') or ''}" for j in jobs]
        vecs = [np.asarray(v) for v in _model().embed([profile_text] + job_texts)]
        q = vecs[0]
        qn = np.linalg.norm(q) or 1.0
        for j, v in zip(jobs, vecs[1:]):
            denom = qn * (np.linalg.norm(v) or 1.0)
            sem = max(0.0, min(float(np.dot(q, v) / denom), 1.0))
            kw = j.get("match_score", 0.0)
            j["match_score"] = round((1 - blend) * kw + blend * sem, 3)
            if sem >= 0.6:
                rs = j.get("match_reasons", [])
                if "Semantic match" not in rs:
                    j["match_reasons"] = (["Semantic match"] + rs)[:4]
        jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        logger.info(f"[embeddings] re-ranked {len(jobs)} jobs (blend={blend})")
    except Exception as e:
        logger.warning(f"[embeddings] rerank failed, keeping keyword order: {e}")
    return jobs
