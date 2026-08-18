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

## Running tests

```bash
pytest
```

Tests use synthetic RSS/Atom strings passed directly to `NewsIndex.add_feed(url, fetch_text=...)` — no network access is required or used in the test suite.

## Making changes

1. Fork the repo and create a branch from `main`.
2. Write or update tests for any behavior change — especially parsing edge
   cases (malformed feeds, missing fields, unusual `<link>` structures) and
   anything touching `fetch`/`assert_fetchable`, since that's the surface
   an untrusted feed URL reaches.
3. Run `pytest` and make sure everything passes.
4. Open a pull request describing the change and why it's needed.

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
