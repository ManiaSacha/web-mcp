# Review — `fix/harden-web-mcp-server`

## What changed

Adds the core single-file MCP server and root project scaffold, with five
correctness/security fixes applied to the original draft of `web_mcp.py`.

**`web_mcp.py` — bug fixes (all verified by tests on `feature/add-web-mcp-tests`):**

1. **RSS `<link>` was being silently blanked.** The original expression
   `link or children.get("id").text if children.get("id") is not None else ""`
   parses as `(link or id_text) if id_exists else ""`. Plain RSS items have no
   `<id>` element, so the condition was false for essentially every RSS article
   and the correctly-parsed link was discarded and replaced with `""`.
   Reproduced standalone before fixing.
2. **`ZeroDivisionError` on stopword-only articles.** An article whose title and
   summary tokenize to nothing produced `norm == 0`, crashing the TF-IDF vector
   normalization and taking down the whole `add_feed` call. Such docs are now
   stored with an empty vector — still visible in `recent()`/`digest()`, just
   unscoreable in `search()`.
3. **Atom entries with multiple `<link>` elements resolved to the wrong URL.**
   Collapsing children into `{local(c): c for c in el}` keeps whichever `<link>`
   appears last in document order, often `rel="self"` or an enclosure rather
   than the human-facing article URL. Added `_entry_link()` which prefers
   `rel="alternate"` (or absent `rel`, which defaults to alternate per the Atom
   spec) and falls back to `guid`/`id` only when no usable link exists at all.
4. **No SSRF guard on `add_feed(url)`.** The server would fetch any URL handed to
   it by an agent — including `file://`, `localhost`, RFC1918 addresses, and the
   `169.254.169.254` cloud metadata endpoint. Added `assert_fetchable()`:
   http/https only, hostname resolved up front and rejected if it maps to a
   loopback/private/link-local/multicast/reserved address.
5. **No resource bounds.** Added a 5 MB cap on fetched feed bodies, an explicit
   fetch timeout, and clamped every tool's `limit` parameter to `MAX_LIMIT`.

Also moved `idf`/`n` computation inside the lock in `search()`, and wrapped the
`add_feed` tool so a fetch failure returns a readable message instead of raising
through the MCP layer.

**Other files:** `pyproject.toml` (hatchling build, `mcp` dependency, pytest
config), `README.md` (tool table + security notes), `CONTRIBUTING.md`,
`.gitignore`.

## Tests

`pytest` — **25 passed**. Note that the tests themselves live on
`feature/add-web-mcp-tests`; this branch was verified with that test file
present in the working tree.

## Known limitations — please read before merging

- **`assert_fetchable` is best-effort, not a sandbox.** It resolves the hostname
  at check time, not fetch time, so a DNS answer that changes between the two
  (DNS rebinding) is not covered. Closing that properly requires pinning the
  resolved IP through to the `urlopen` call.
- **Redirects are not re-validated.** `urllib.request` follows 30x automatically
  and does not re-run `assert_fetchable` on the redirect target, so a remote
  server can 302 a passed check toward an internal address. This is documented
  in the `security-reviewer` agent as a known gap rather than fixed here.
- The index is in-memory only; restarting the server re-fetches everything.

## Not done here

No PR opened and nothing merged — per the git-pipeline protocol, opening the PR
and merging into `main` is yours to do.
