#!/usr/bin/env bash
# Check out automation/daily-snapshots and merge main into it.
# This script does not push. Snapshot conflicts take main's copy; the catalog
# is rebuilt by the fetch that runs next. Any other conflict fails the job.
set -euo pipefail

BRANCH="automation/daily-snapshots"

if [ "${GITHUB_REF:-}" != "refs/heads/main" ]; then
  echo "Refusing to prepare a data branch from ${GITHUB_REF:-<unset>}."
  exit 1
fi

git fetch origin main

if git fetch origin "$BRANCH"; then
  git checkout -B "$BRANCH" "origin/${BRANCH}"
  if git merge origin/main --no-edit; then
    exit 0
  fi
  echo "Merging main hit conflicts. Resolving only files under data/."
  conflicted="$(git diff --name-only --diff-filter=U)"
  if [ -z "$conflicted" ]; then
    echo "Merge failed without listing conflicted files."
    exit 1
  fi
  while IFS= read -r path; do
    [ -z "$path" ] && continue
    case "$path" in
      data/raw/*|data/normalized/*)
        if ! git checkout --theirs -- "$path"; then
          echo "Could not take main's version of ${path}."
          exit 1
        fi
        if [ -e "$path" ]; then
          git add -- "$path"
        else
          git rm -f -- "$path"
        fi
        ;;
      data/catalog/*|data/jobradar.sqlite)
        if git checkout --ours -- "$path"; then
          if [ -e "$path" ]; then
            git add -- "$path"
          else
            git rm -f -- "$path"
          fi
        else
          git rm -f -- "$path"
        fi
        ;;
      *)
        echo "Refusing to resolve a conflict in ${path}."
        exit 1
        ;;
    esac
  done <<< "$conflicted"
  remaining="$(git diff --name-only --diff-filter=U)"
  if [ -n "$remaining" ]; then
    echo "Unresolved conflicts remain:"
    printf '%s\n' "$remaining"
    exit 1
  fi
  git commit -m "Merge main into the daily snapshot branch"
else
  git checkout -B "$BRANCH" origin/main
fi
