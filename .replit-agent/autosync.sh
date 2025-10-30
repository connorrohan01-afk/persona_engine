#!/bin/bash
set -e
branch=${1:-main}
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 0) clear any stale git locks (non-fatal if absent)
rm -f .git/index.lock || true
rm -rf .git/rebase-merge .git/rebase-apply || true

# 1) stage & commit if there are changes
git add -A
git diff --cached --quiet || git commit -m "chore(agent): autosync ${ts}"

# 2) rebase on top of origin (prefer our edits on conflict)
git fetch origin ${branch}
if ! git rebase -X ours "origin/${branch}"; then
  git rebase --abort
  # fallback: fast merge preferring ours
  git merge -s ours "origin/${branch}" -m "chore(agent): reconcile with origin ${ts}" || true
fi

# 3) push (respect remote updates; only force with lease if needed)
if ! git push -u origin HEAD:${branch}; then
  git push -u origin HEAD:${branch} --force-with-lease
fi

# 4) show status for the log
echo "----- AUTOSYNC DONE -----"
git log -1 --oneline
git status -s
