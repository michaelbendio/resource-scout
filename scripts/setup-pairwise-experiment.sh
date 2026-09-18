#!/usr/bin/env bash
set -euo pipefail

ROOT="${HOME}/resource-scout"
WORKTREE="${HOME}/resource-scout-pairwise"
STAMP="$(date +%Y%m%d-%H%M%S)"
BASELINE_ROOT="${HOME}/resource-scout-baselines"
SNAPSHOT="${BASELINE_ROOT}/st-george-${STAMP}"
DB="${ROOT}/data/research-agent.sqlite3"
BRANCH="pairwise-research-experiment"

if ! git -C "${ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Expected Git working tree at ${ROOT}" >&2
  exit 1
fi
if [[ ! -f "${DB}" ]]; then
  echo "Scout database not found at ${DB}" >&2
  exit 1
fi
if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 is required for a consistent live database backup" >&2
  exit 1
fi

mkdir -p "${SNAPSHOT}"

echo "Saving Scout progress..."
curl -fsS http://127.0.0.1:8765/api/scout-progress   > "${SNAPSHOT}/scout-progress.json" || {
    echo "Could not read Scout progress from port 8765" >&2
    exit 1
  }

echo "Backing up live SQLite database..."
sqlite3 "${DB}" ".backup '${SNAPSHOT}/research-agent.sqlite3'"

(
  cd "${ROOT}"
  git rev-parse HEAD > "${SNAPSHOT}/main-head.txt"
  git status --short --branch > "${SNAPSHOT}/git-status.txt"
  git branch --show-current > "${SNAPSHOT}/branch.txt"
)

shasum -a 256 "${SNAPSHOT}/research-agent.sqlite3"   > "${SNAPSHOT}/SHA256SUMS.txt"

echo "Fetching experiment branch..."
git -C "${ROOT}" fetch origin "${BRANCH}"

if [[ -d "${WORKTREE}" ]]; then
  echo "Worktree already exists at ${WORKTREE}"
else
  if git -C "${ROOT}" show-ref --verify --quiet "refs/heads/${BRANCH}"; then
    git -C "${ROOT}" worktree add "${WORKTREE}" "${BRANCH}"
  else
    git -C "${ROOT}" worktree add -b "${BRANCH}" "${WORKTREE}" "origin/${BRANCH}"
  fi
fi

echo "Running pairwise branch tests..."
(
  cd "${WORKTREE}"
  python3 -m unittest discover -s tests -v
)

echo
echo "Baseline snapshot: ${SNAPSHOT}"
echo "Pairwise worktree: ${WORKTREE}"
echo "Scout server was not stopped or modified."
