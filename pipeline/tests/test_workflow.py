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
    assert 'Refusing to push the default branch.' in publish
