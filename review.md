# Review — `feature/add-web-mcp-tests`

Branched from `fix/harden-web-mcp-server` (the tests import `web_mcp`, so they
can't stand alone on `main`). Merge that branch first.

## What changed

Adds `tests/test_web_mcp.py` — 25 tests, no network access anywhere in the
suite. Feeds are synthetic XML strings passed straight to
`NewsIndex.add_feed(url, fetch_text=...)`, so the suite is deterministic and
runs offline.

Coverage by area:

- **Parsing (5 tests)** — RSS and Atom field extraction, malformed XML raising,
  plus explicit regression tests for the two link-resolution bugs fixed on the
  server branch (RSS link being blanked when no `<guid>` is present; Atom
  `rel="self"` winning over `rel="alternate"`). Both are labelled as regression
  tests in their docstrings so a future refactor doesn't quietly delete them.
- **Tokenizing (1 test)** — stopword and short-token filtering.
- **Index behavior (10 tests)** — add/remove feed, the stopword-only
  `ZeroDivisionError` regression, search ranking, empty-query handling, recency
  boost ordering, trending, digest with no recent articles, source health.
- **SSRF hardening (9 tests)** — parametrized rejection of non-http schemes
  (`file://`, `ftp://`, `gopher://`), loopback/private/link-local hosts
  including the `169.254.169.254` cloud metadata address, and URLs with no
  hostname.

## Tests

`pytest` — **25 passed**.

## One thing worth flagging

While writing these I hit a genuine failure in
`test_search_recency_boosts_newer_matching_doc`: my fixture used "Rockets" in
one article and searched for "rocket". The tokenizer does no stemming, so those
are distinct terms and only one article matched. **The test was wrong, not the
server** — I fixed the fixture rather than the ranking code. Calling it out
because it's a real property of the search: `search("rocket")` will not match an
article titled "Rockets ...". If that surprises you, stemming is a reasonable
follow-up feature, but it's a behavior change, not a bug fix, so I left it.

## Not done here

No PR opened and nothing merged — that's yours.
