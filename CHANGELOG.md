# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note on names:** the project and its Claude Code plugin are `web-mcp`; the
> PyPI distribution is **`feed-mcp`**, because PyPI rejects `web-mcp` as too
> similar to an unrelated existing `webmcp` package.

## [Unreleased]

### Added
- Continuous integration: tests on Python 3.10–3.13 on Linux, plus macOS and
  Windows on 3.12; `ruff` lint; a packaging job that installs the built wheel
  and confirms both console scripts run.
- `scripts/validate_plugin.py`, run in CI, checking manifest fields, skill and
  agent frontmatter, plugin layout, version sync across all four places the
  version appears, and that `.mcp.json`'s command is actually shipped as a
  console script.
- Issue templates, including a dedicated feed-compatibility form that collects
  the URL and snippet needed to turn a report into a test fixture.
- Pull request template, `CODEOWNERS`, Dependabot, release-note categories,
  and a code of conduct.

### Changed
- `parse_feed` binds `children` as a default argument rather than closing over
  the loop variable, removing a latent late-binding hazard.

## [0.2.0] - 2026-08-19

### Added
- Distributed as a Claude Code plugin: `.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`, and `.mcp.json`, so installing the plugin
  registers the MCP server along with the bundled skills and agents. Enabling
  it prompts for a starting feed list.
- `install.sh` and `install.ps1`, which locate a suitable Python, install, and
  verify the command landed on `PATH`.
- Tag-triggered PyPI release workflow using Trusted Publishing, gated on the
  tag matching `pyproject.toml`.
- `SECURITY.md` and `docs/SECURITY-MODEL.md`.

### Security
- **Fixed DNS rebinding in feed fetching.** The hostname was validated and then
  re-resolved by `urllib` at connect time, so the address that was checked was
  not necessarily the address that was dialed. `assert_fetchable` now returns
  the address it approved and the connection is made to that address, with TLS
  still validating certificates against the hostname.
- **Fixed redirects bypassing the SSRF check.** `urllib` followed `30x`
  responses without re-validating them, so a public URL could redirect a fetch
  to an internal host such as `169.254.169.254`. Redirects are now followed
  manually, re-validated at every hop, and capped at 5.
- A URL is rejected when *any* resolved address is non-public, not just the
  first, closing a bypass for hosts returning mixed public/private records.
- IPv4-mapped IPv6 addresses are unwrapped before classification.

### Changed
- `agents/skills` moved from `.claude/` to the repository root, as Claude Code
  discovers plugin components at the plugin root.
- The `research-digest` skill is now `feed-digest`.
- Review files moved from a fixed `review.md` to `reviews/<branch-name>.md`,
  which was causing an add/add merge conflict on every pull request.

## [0.1.0] - 2026-08-18

Initial release: single-file MCP server with feed management, recency-boosted
TF-IDF search, trending topics, markdown digests, source health monitoring, and
background refresh, plus an offline test suite and the first Claude Code skills
and agents.

### Fixed
- RSS `<link>` was blanked for any item without a `<guid>`, due to an
  operator-precedence bug — which was most RSS items.
- `ZeroDivisionError` when an article's title and summary tokenized to nothing.
- Atom entries with several `<link>` elements resolved to whichever appeared
  last rather than `rel="alternate"`.

### Security
- Scheme allowlist, public-address requirement, a 5 MB body cap, explicit fetch
  timeouts, and clamped `limit` arguments.

[Unreleased]: https://github.com/ManiaSacha/web-mcp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ManiaSacha/web-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ManiaSacha/web-mcp/releases/tag/v0.1.0
