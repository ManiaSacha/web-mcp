# Contributing to web-mcp

Thanks for considering a contribution.

## Philosophy

`web_mcp.py` is intentionally a single, readable file with no non-stdlib
dependency beyond `mcp`. Before adding a dependency or splitting the file up,
open an issue to discuss — the simplicity is the point.

## Setup

```bash
git clone https://github.com/ManiaSacha/web-mcp.git
cd web-mcp
pip install -e ".[dev]"
```

## Checks

These three are what CI runs; all of them work offline.

```bash
pytest                              # 53 tests, no network access
ruff check .                        # lint
python scripts/validate_plugin.py   # manifests, frontmatter, version sync
```

Tests use synthetic RSS/Atom strings passed directly to `NewsIndex.add_feed(url, fetch_text=...)`, and fetch-level tests inject fake resolvers and connections — no network access is required or used in the test suite. Please keep it that way; a test that reaches the network is flaky by construction and fails for anyone offline.

`validate_plugin.py` catches the class of mistake that otherwise fails *silently*: a skill whose frontmatter `name` doesn't match its directory simply never loads, with no error anywhere.

A few ruff rules are deliberately suppressed at the site with `# noqa` and a reason — blind excepts in `parse_date` and the background refresh loop are intentional. If you need a new suppression, put it at the line with a comment saying why, rather than widening the ignore list in `pyproject.toml`.

## Making changes

1. Fork the repo and create a branch from `main`.
2. Write or update tests for any behavior change — especially parsing edge
   cases (malformed feeds, missing fields, unusual `<link>` structures) and
   anything touching `fetch`/`assert_fetchable`/`open_pinned`, since that's the
   surface an untrusted feed URL reaches. Read
   [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md) before changing those.
3. Run the three checks above.
4. Add a `CHANGELOG.md` entry under `## [Unreleased]`.
5. Open a pull request describing the change and why it's needed.

## Versioning

The version appears in four places and CI fails if they disagree:
`pyproject.toml` (the version of record), `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, and `USER_AGENT` in `web_mcp.py`.
`python scripts/validate_plugin.py` checks all four.

## Reporting security issues

If you find a way to make `add_feed`/`fetch` reach a host it shouldn't (SSRF),
cause excessive memory/CPU from a hostile feed, or otherwise misbehave on
untrusted input, please open an issue describing the scenario. This is a
local, single-user tool, so there's no formal disclosure process — just
flag it clearly as a security issue in the title.

## Code style

- No comments explaining *what* code does — names should make that clear.
  Comments are for non-obvious *why* (a workaround, an invariant, a subtle
  parsing gotcha).
- Keep new tools small and composable, matching the existing `@mcp.tool()`
  functions in `web_mcp.py`.
