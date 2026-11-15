import re
from pathlib import Path

from jobradar.paths import find_repo_root


def test_daily_workflow_pins_actions_and_does_not_push_main():
    root = find_repo_root()
    workflow = (root / ".github" / "workflows" / "daily-fetch.yml").read_text(encoding="utf-8")
    publish = (root / ".github" / "scripts" / "publish-data-branch.sh").read_text(encoding="utf-8")

    uses = []
    for line in workflow.splitlines():
        stripped = line.strip()
        if stripped.startswith("uses:"):
            uses.append(stripped.split(" # ", 1)[0])
    assert uses
    for action in uses:
        assert re.fullmatch(r"uses: [\w./-]+@[0-9a-f]{40}", action), action

    assert "cron:" in workflow
    assert "contents: read" in workflow
    assert "contents: write" in workflow
    assert "pull-requests: write" in workflow
    assert "${{ secrets." not in workflow
    assert "GH_TOKEN: ${{ github.token }}" in workflow

    assert 'BRANCH="automation/daily-snapshots"' in publish
    assert 'git push origin "HEAD:${BRANCH}"' in publish
    assert "git push origin main" not in publish
    assert "git push origin HEAD:main" not in publish
    assert "--force" not in publish
    assert "Refusing to push the default branch." in publish
    assert "Allow GitHub Actions to create and approve pull requests" in publish
    assert "personal access token" in publish
    assert "secrets." not in publish


def test_ci_workflow_is_least_privilege_and_runs_the_checks():
    root = find_repo_root()
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    uses = []
    for line in workflow.splitlines():
        stripped = line.strip()
        if stripped.startswith("uses:"):
            uses.append(stripped.split(" # ", 1)[0])
    assert uses
    for action in uses:
        assert re.fullmatch(r"uses: [\w./-]+@[0-9a-f]{40}", action), action

    assert "pull_request:" in workflow
    assert "- main" in workflow
    assert "contents: read" in workflow
    assert "contents: write" not in workflow
    assert "pull-requests:" not in workflow
    assert "cancel-in-progress: true" in workflow
    assert "${{ secrets." not in workflow
    assert "uv run pytest" in workflow
    assert "npm ci" in workflow
    assert "npm run lint" in workflow
    assert "npm run typecheck" in workflow
    assert "npm test" in workflow
    assert "npm run build" in workflow
    assert "playwright test --project=chromium" in workflow

    upload_at = workflow.index("actions/upload-artifact@")
    assert "if: failure()" in workflow[max(0, upload_at - 250) : upload_at]
    assert "playwright-report" in workflow
