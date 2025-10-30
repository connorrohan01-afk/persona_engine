#!/bin/bash
# --- sanitize, squash, and push safely ---
set -euo pipefail

# 0) Safety backup
git branch backup/$(date +%Y%m%d-%H%M%S) || true

# 1) Clean up any stuck git state
rm -f .git/index.lock || true
git rebase --abort || true
git merge --abort || true
rm -rf .git/rebase-merge .git/rebase-apply || true

# 2) Redact secrets in working tree (Anthropic key & similar)
#   Tweak/add patterns if you know other secret names.
[ -f DEPLOYMENT_CONFIG.txt ] && \
  sed -i -E 's/(^|\s)ANTHROPIC_API_KEY\s*=\s*.*/\1ANTHROPIC_API_KEY=REDACTED/' DEPLOYMENT_CONFIG.txt || true

# belt-and-braces: nuke any literal sk-ant-… tokens anywhere
perl -0777 -pe 's/sk-ant-[A-Za-z0-9_\-]+/REDACTED/g' -i $(git ls-files) || true

git add -A
git commit -m "sanitize: redact secrets from tree" || true

# 3) Build a fresh, single-commit history (orphan branch) from the sanitized tree
git checkout --orphan sanitized
git rm -rf --cached . >/dev/null 2>&1 || true
git add -A
git commit -m "build: sanitized tree (no secrets, squashed history)"

# 4) Push sanitized -> main (rewrite remote safely)
git push -u origin sanitized:main --force-with-lease

# 5) Return to main locally on the same commit id as remote
git checkout -B main

# 6) Show status for confirmation
git log --oneline -3
git status
echo "✅ Push complete. Remote 'main' now has a single sanitized commit."
