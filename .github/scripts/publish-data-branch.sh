#!/usr/bin/env bash
# Commit data/ onto automation/daily-snapshots and open a pull request.
# The push refspec is that branch. main is never the destination.
set -euo pipefail

BRANCH="automation/daily-snapshots"

if [ "${GITHUB_REF:-}" != "refs/heads/main" ]; then
  echo "Refusing to publish from ${GITHUB_REF:-<unset>}."
  exit 1
fi

current="$(git branch --show-current)"
if [ "$current" != "$BRANCH" ]; then
  echo "Refusing to publish from branch ${current}."
  exit 1
fi

case "$BRANCH" in
  main|master|refs/heads/main|refs/heads/master)
    echo "Refusing to push the default branch."
    exit 1
    ;;
esac

git add -A -- data
while IFS= read -r path; do
  [ -z "$path" ] && continue
  case "$path" in
    data/*) ;;
    *)
      echo "Refusing to commit ${path}, which is outside data/."
      exit 1
      ;;
  esac
done < <(git diff --cached --name-only)

if git diff --cached --quiet; then
  echo "No data changes to commit."
else
  git commit -m "chore: store daily job snapshot"
fi

if git rev-parse --verify "origin/${BRANCH}" >/dev/null 2>&1; then
  ahead_of_remote="$(git rev-list --count "origin/${BRANCH}..HEAD")"
else
  ahead_of_remote="$(git rev-list --count "origin/main..HEAD")"
fi

if [ "$ahead_of_remote" != "0" ]; then
  git push origin "HEAD:${BRANCH}"
else
  echo "Remote ${BRANCH} already has this commit. Not pushing."
fi

ahead_of_main="$(git rev-list --count "origin/main..HEAD")"
if [ "$ahead_of_main" = "0" ]; then
  echo "Branch matches main. No pull request to open."
  exit 0
fi

if url="$(gh pr view "$BRANCH" --json url --jq .url 2>/dev/null)"; then
  echo "Pull request already open: ${url}"
  exit 0
fi

stamp="$(date -u +%Y-%m-%d)"
body="$(cat <<EOF
Daily fetch for ${stamp}.

This pull request is opened by the daily workflow. The workflow pushes \`automation/daily-snapshots\` and does not push \`main\`.

What landed:

- \`data/raw/${stamp}.json\`, \`data/normalized/${stamp}.json\`, and \`data/normalized/${stamp}.csv\` are that UTC date's snapshot. Earlier dates are left in place.
- \`data/catalog/postings.json\` is the deduped catalog. The same canonical URL, or the same company and title, stays one posting. \`days.new\` is the trend count; \`days.seen_again\` is reposts.
- \`data/jobradar.sqlite\` is the same catalog in SQLite. Deleting it and running \`uv run jobradar fetch\` rebuilds it from the snapshot files.

Retention: every daily snapshot stays in git. Descriptions and logos are already omitted. Revisit that if \`data/\` grows.

No API keys. Remotive, Remote OK, and Arbeitnow are public endpoints, and the run uses the workflow's \`GITHUB_TOKEN\` only to push this branch and open the pull request.
EOF
)"

if ! created="$(gh pr create --base main --head "$BRANCH" --title "chore: daily job snapshot ${stamp}" --body "$body" 2>&1)"; then
  printf '%s\n' "$created" >&2
  case "$created" in
    *"not permitted to create or approve pull requests"*)
      settings="${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-Abdullah4589/junior-job-radar}/settings/actions"
      cat <<EOF >&2

The data branch was pushed. GitHub refused to let this workflow open the pull request.

The job already grants pull-requests: write. That scope is on the token, and it is not enough. The repository owner has to enable a separate setting, which is off by default on a personal account:

  Settings → Actions → General → Workflow permissions →
  Allow GitHub Actions to create and approve pull requests

Save it here, then rerun the workflow:
  ${settings}

This workflow does not use a personal access token or another account to bypass that setting. After it is saved, the next run opens the pull request for the commits already on ${BRANCH}.
EOF
      ;;
  esac
  exit 1
fi

echo "Opened pull request: ${created}"
