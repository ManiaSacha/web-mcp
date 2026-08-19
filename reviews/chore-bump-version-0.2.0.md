# Review — `chore/bump-version-0.2.0`

Prepares the first PyPI release. Version only — no behavior changes.

## Why 0.2.0 and not 0.1.0

A `v0.1.0` tag already exists on the remote, pointing at `8a4b475` (the PR #4
merge). It predates `.github/workflows/release.yml` entirely, so no publish
workflow ever ran for it, and re-pushing an existing tag triggers nothing.

There are 13 commits on `main` past that tag, including the whole plugin
distribution and both SSRF fixes. Retagging `v0.1.0` onto today's `main` would
rewrite what an already-published tag and GitHub Release refer to. Cutting
`0.2.0` leaves that history intact, and the content justifies a minor bump on
its own: an installable Claude Code plugin, PyPI packaging, and two security
fixes.

## What changed

Five files carry the version, and the release workflow aborts if `pyproject`
disagrees with the tag:

| File | Field |
|---|---|
| `pyproject.toml` | `version` — the version of record |
| `.claude-plugin/plugin.json` | `version` |
| `.claude-plugin/marketplace.json` | plugin entry `version` |
| `web_mcp.py` | `USER_AGENT` (`web-mcp/0.2`) — what feed operators see in their logs |
| `SECURITY.md` | supported-versions table |

## Verification

- All five references agree, checked programmatically rather than by eye.
- Simulated the workflow's own gate: tag `v0.2.0` → `0.2.0` vs pyproject
  `0.2.0` → **PASS**.
- 53 tests pass.
- `python -m build` produces `web_mcp-0.2.0` sdist and wheel; `twine check`
  passes on both.

## No CHANGELOG entry

`agents/git-pipeline.md` says to add a changelog entry if `CHANGELOG.md`
exists and not to invent one otherwise. It doesn't exist yet — it's scheduled
for Phase 3. Following the rule as written rather than quietly widening this
branch; the GitHub Release notes cover 0.2.0 in the meantime.

## Release steps after this merges

1. Register the PyPI pending publisher first (project `web-mcp`, owner
   `ManiaSacha`, repo `web-mcp`, workflow `release.yml`, environment `pypi`).
   Without it the publish job fails at the OIDC exchange.
2. `git checkout main && git pull && git tag v0.2.0 && git push origin v0.2.0`
3. The workflow verifies the version, runs the tests, builds, `twine check`s,
   then publishes — creating the PyPI project on first success.

`web-mcp` was confirmed available on PyPI: both the JSON API and the simple
index return 404.
