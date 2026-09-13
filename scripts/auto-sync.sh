#!/usr/bin/env bash
# Auto-commit + push the residency wiki database to GitHub.
# Call after any weekly monitor update. Records a dated commit of all changes.
set -euo pipefail

WIKI="${WIKI_PATH:-$HOME/wiki}"
cd "$WIKI"

# Load GH_TOKEN from ~/.hermes/.env (secret, outside the repo) if not already set
if [ -z "${GH_TOKEN:-}" ] && [ -f "$HOME/.hermes/.env" ]; then
  # shellcheck disable=SC1090
  set -a; source "$HOME/.hermes/.env"; set +a
fi

if [ -z "${GH_TOKEN:-}" ]; then
  echo "ERROR: GH_TOKEN not set (put it in ~/.hermes/.env or export it)" >&2
  exit 1
fi

# Commit if there are changes (tracked OR untracked/new files)
if git diff --quiet HEAD && [ -z "$(git status --porcelain)" ]; then
  echo "No changes to push on $(date -u +%Y-%m-%dT%H:%MZ)"
  exit 0
fi
git add -A
git commit -m "update: residency conditions snapshot $(date -u +%Y-%m-%dT%H:%MZ)"

# Push using a token-in-URL ONLY at push time (never stored in .git/config).
# Origin URL stays token-free; this builds a transient authenticated URL.
PUSH_URL="https://x-access-token:${GH_TOKEN}@github.com/MastPeace/residency-vault.git"
git push "$PUSH_URL" main
echo "Pushed snapshot $(date -u +%Y-%m-%dT%H:%MZ)"