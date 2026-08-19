# Review — `chore/bump-version-0.2.1`

Version-only branch. Cuts the real first release after the `v0.2.0` tag was
found to point at a commit that predates the `mcp` 2.0 compatibility fix.

## Why 0.2.1, not a moved 0.2.0

`v0.2.0` already exists as a pushed tag, pointing at `be20cb9` — before PR #10
(which contains the `mcp` 2.0 fix) merged. Confirmed on PyPI that nothing was
ever actually published under it (`feed-mcp` still 404s), which lines up with
the release workflow's own test gate catching the same import failure CI did
and refusing to publish.

Given the choice between force-moving the existing tag or cutting a fresh one,
went with fresh: `v0.1.0` and the stale `v0.2.0` stay exactly as they are —
unpublished, harmless, no history rewritten — and `v0.2.1` becomes the actual
first release.

## What changed

Three of the five files that carry the version needed edits; the other two
already covered a patch bump:

| File | Change |
|---|---|
| `pyproject.toml` | `0.2.0` → `0.2.1` |
| `.claude-plugin/plugin.json` | `0.2.0` → `0.2.1` |
| `.claude-plugin/marketplace.json` | `0.2.0` → `0.2.1` |
| `web_mcp.py` `USER_AGENT` | unchanged (`web-mcp/0.2` — minor-only, doesn't track patch) |
| `SECURITY.md` supported-versions | unchanged (`0.2.x` already covers `0.2.1`) |

`CHANGELOG.md`: the `[Unreleased]` content (the mcp 2.0 fix, CI, community
health files) is now under a real `## [0.2.1]` heading, dated today, with a
note explaining why `0.2.0` is skipped on PyPI so a reader comparing the
changelog to the PyPI version list isn't confused by the gap.

## Verification

Given that the *previous* version bump branch was verified exactly this way
and still shipped a real bug, verification here goes further than a version-sync
check — it reproduces what `release.yml` will actually do, in a genuinely
clean environment:

1. Fresh venv, `pip install -e ".[dev]"` — resolved `mcp==2.0.0`, the exact
   version that broke the previous attempt.
2. `pytest -q` (the verify job's test step) — **53 passed**.
3. `python -m build` + `twine check` (the build job) — both distributions pass.
4. Installed the built wheel with `--no-deps` and ran both console scripts —
   **`web-mcp --help` and `feed-mcp --help` both work.**

Also re-ran the programmatic version-sync check and the workflow's own
tag-vs-version gate simulation: tag `v0.2.1` → `0.2.1` vs pyproject `0.2.1` →
**PASS**. `scripts/validate_plugin.py` (36 checks) and `ruff check .` both pass.

## Release steps after this merges

1. Confirm the pending publisher is still registered — project `feed-mcp`,
   owner `ManiaSacha`, repo `web-mcp`, workflow `release.yml`, environment
   `pypi`. Already done per the earlier phase; nothing changes here.
2. `git checkout main && git pull && git tag v0.2.1 && git push origin v0.2.1`
3. Watch Actions. `v0.1.0` and `v0.2.0` remain on GitHub as tags with no
   corresponding PyPI release — that's expected and doesn't need cleanup.
