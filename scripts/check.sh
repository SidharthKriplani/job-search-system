#!/usr/bin/env bash
# Pre-push gate — run this before every `git push`. Same checks as CI, locally,
# so you catch a break in ~30s instead of finding out from a red deploy.
#   ./scripts/check.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "▶ Python tests (matching engine)…"
python3 -m pytest -q

echo "▶ Frontend type-check…"
cd frontend
[ -d node_modules ] || npm install --no-audit --no-fund
npx tsc --noEmit

echo "✅ All checks passed — safe to push."
