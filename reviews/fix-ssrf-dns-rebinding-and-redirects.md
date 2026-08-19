# Review — `fix/ssrf-dns-rebinding-and-redirects`

Phase 2: closes the two SSRF gaps that `agents/security-reviewer.md` and the
README both documented as open.

## The two gaps

**DNS rebinding.** `assert_fetchable()` resolved the hostname, then handed the
*URL* to `urllib.request.urlopen()`, which resolved it again at connect time.
Between those two lookups DNS can answer differently, so the address that was
checked was not necessarily the address that was connected to. No amount of
care inside the check closes this, because the check and the connection were
looking at separate answers.

**Redirects.** `urllib` follows `30x` automatically and never re-runs our
check when it does. A URL that passed validation could answer
`302 Location: http://169.254.169.254/` and the fetch would follow it straight
into the cloud metadata endpoint.

## How they're closed

`assert_fetchable()` now returns `(parsed, ip)` — the address it approved — and
`open_pinned()` builds the socket against that IP directly, so there is no
second name resolution. TLS is unaffected: the socket is wrapped with
`server_hostname` set to the real hostname, so SNI and certificate validation
still happen against the name, not the address.

`fetch()` no longer delegates redirects. It follows them in an explicit loop
and sends every hop back through `assert_fetchable()`, capped at
`MAX_REDIRECTS = 5`, with a missing `Location` raising rather than looping.

This meant replacing `urllib.request` with `http.client` plus a hand-built
socket. That is more code, but the alternative — subclassing urllib's redirect
and connection handlers — buries the security-relevant logic in framework
plumbing. An explicit loop you can read top to bottom seemed the better trade
for this project.

Two further hardening changes fell out of the work:

- `assert_fetchable` now rejects when **any** resolved address is non-public,
  not just the first. A split-horizon host returning one public and one private
  record was previously bypassable by retrying.
- Address classification unwraps IPv4-mapped IPv6 addresses, so
  `::ffff:127.0.0.1` is treated as loopback. Python 3.13 already classifies
  these correctly; the explicit unmapping removes the dependency on that
  behavior holding for every version in our supported 3.10+ range, which I
  could not verify locally.

## Verification

- **53 tests pass**, up from 25. The 28 new ones are offline, using injected
  resolver and connection fakes.
- Named regression tests for each gap: `test_open_pinned_dials_the_validated_ip_not_the_hostname`,
  `test_fetch_revalidates_each_redirect_hop`,
  `test_fetch_blocks_redirect_to_cloud_metadata_endpoint`, plus split-horizon
  DNS, protocol-relative redirects, chain limits, and the size cap.
- **Live smoke test** against real servers, since the fake-based tests can't
  prove the hand-rolled client actually speaks HTTP: `https://hnrss.org/frontpage`
  (20 items) and `https://github.blog/feed/` (10 items) both fetch and parse.
  `http://github.blog/feed/` was included deliberately — it redirects to HTTPS,
  exercising the redirect path with a scheme change, and it works.
- **Live block test**: `http://localhost:8000/feed`, `http://169.254.169.254/latest/meta-data/`,
  `file:///etc/passwd`, and `http://[::ffff:127.0.0.1]/feed` are each refused
  end-to-end through `fetch()` with a clear message.
- `python -m build` still produces both distributions.

## Docs

- `SECURITY.md` — reporting process (GitHub private advisories) and threat model.
- `docs/SECURITY-MODEL.md` — the four checks explained, including *why*
  pinning is needed, plus a "Known limits" section and a table mapping each
  guarantee to the test that guards it.
- README security section rewritten — it previously described both of these as
  known limitations.
- `agents/security-reviewer.md` updated. This mattered more than it looks: the
  agent instructed reviewers to *expect* these gaps and to be skeptical of
  fixes. Left unchanged it would have told a future reviewer that working code
  was wrong. It now instructs them to verify pinning and manual redirects are
  still in place, and flags reintroducing any auto-redirecting HTTP client as
  a regression.

## Known limits, unchanged or newly stated

- The 5 MB cap bounds what is buffered, not what is transferred; a slow-drip
  server can hold a connection until the socket timeout fires, worst case
  roughly `MAX_REDIRECTS × FETCH_TIMEOUT`.
- A publicly-routable address is not automatically a safe one — if your network
  routes public addresses to hosts you consider internal, address
  classification cannot know that. Egress rules are the right tool.
- Feed *content* remains untrusted data.

## Note on the single-file philosophy

`web_mcp.py` is now 532 lines, up from ~450. Still comfortably "one readable
file", but this is the growth the plan predicted. The v1.0 decision about
splitting into `src/web_mcp/` is worth revisiting once Phase 4 adds
persistence and BM25 — as a deliberate call, not by accretion.

## Not in this branch

Phase 3 (CI matrix, issue/PR templates, dependabot, CODEOWNERS, CHANGELOG) and
Phase 4 (persistence, BM25, conditional GET, MCP resources/prompts).
