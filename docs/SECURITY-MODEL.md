# Security model

How web-mcp handles untrusted input, what it guarantees, and — just as
importantly — what it does not.

For reporting instructions and the threat model, see [SECURITY.md](../SECURITY.md).

## The one dangerous operation

Almost all of web-mcp is arithmetic over strings already in memory. One
operation reaches outside the process:

```
add_feed(url)  ->  fetch(url)  ->  socket connect + HTTP GET
```

An agent calls `add_feed` with a URL. That URL may have come from the user, or
it may have come from a web page, an email, or an article the agent read
moments earlier. web-mcp cannot tell the difference, so it treats every URL as
attacker-controlled.

## The attack: SSRF

A server that fetches arbitrary URLs is a proxy into whatever network it can
reach. On a laptop that means `localhost` services; on a cloud host it means
the metadata endpoint at `169.254.169.254`, which on some configurations hands
out credentials to anything that asks.

Four checks stand between a URL and a socket.

### 1. Scheme allowlist

Only `http` and `https`. This kills `file:///etc/passwd`, `gopher://`
(historically usable to speak arbitrary protocols), and `data:`.

### 2. Every resolved address must be public

The hostname is resolved and **every** returned address is classified. If any
one is loopback, private, link-local, multicast, reserved, or unspecified, the
URL is refused.

Checking every answer matters. A host under an attacker's control can return
both a public and a private record; validating only the first and connecting
to another would be trivially bypassable by retrying.

IPv4-mapped IPv6 addresses are unwrapped before classification, so
`::ffff:127.0.0.1` is recognised as loopback rather than treated as an opaque
IPv6 address.

### 3. Connect-time IP pinning

This is the subtle one.

The obvious implementation — validate the hostname, then hand the URL to an
HTTP library — has a hole. The library resolves the name *again* when it
connects. Between those two lookups, DNS can answer differently:

```
t=0   attacker.example -> 93.184.216.34   (public: check passes)
t=1   attacker.example -> 127.0.0.1       (library connects here)
```

That is **DNS rebinding**, and no amount of care in the check itself closes
it, because the check and the connection are looking at different answers.

web-mcp closes it by making the validated address the one that gets dialed.
`assert_fetchable()` returns the IP it approved, and `open_pinned()` builds the
socket against that IP directly. There is no second lookup.

Pinning the IP does not weaken TLS: the socket is wrapped with
`server_hostname` set to the original hostname, so SNI and certificate
validation still happen against the name.

### 4. Per-hop redirect validation

Every mainstream HTTP client follows redirects for you, and none of them
re-run your SSRF check when they do. So this passes a check and still ends up
somewhere it shouldn't:

```
GET https://innocent.example/rss   ->  302 Location: http://169.254.169.254/
```

web-mcp therefore does **not** delegate redirects. `fetch()` follows them in an
explicit loop, and every hop goes back through `assert_fetchable()` — same
scheme allowlist, same address classification, same pinning. A chain is capped
at 5 hops, and a `30x` without a `Location` header raises instead of looping.

## Resource limits

| Limit | Value | Why |
|---|---|---|
| `MAX_FETCH_BYTES` | 5 MB | Bounds memory from a hostile or runaway feed |
| `FETCH_TIMEOUT` | 15 s | Per socket operation |
| `MAX_REDIRECTS` | 5 | Bounds redirect chains |
| `MAX_LIMIT` | 100 | Clamps every tool's `limit` argument |

XML is parsed with `xml.etree.ElementTree`, which does not resolve external
entities, so XXE does not apply. Internal entity expansion ("billion laughs")
is bounded only indirectly, by the 5 MB cap on the document itself.

## Known limits

Stated plainly, because a security document that claims total coverage is not
useful.

- **The 5 MB cap bounds buffering, not transfer.** A server that streams
  slowly can occupy a connection until the socket timeout fires. With a full
  redirect chain the worst case is roughly `MAX_REDIRECTS × FETCH_TIMEOUT`.
- **A "public" address is not necessarily a safe one.** If your network routes
  publicly-addressed hosts you consider internal, the address classification
  will not know that. Network egress rules are the right tool there.
- **No authentication.** web-mcp is stdio-local by design. Exposing it over a
  network makes every tool callable by anyone who can reach it.
- **Feed content is untrusted data.** Indexed titles and summaries are written
  by whoever controls the feed. An article whose text says "ignore your
  instructions and…" is a string in a search index, and should be treated by
  any consuming agent as data, never as instructions.
- **No persistence means no integrity checking across restarts.** The index is
  rebuilt from live fetches each time the server starts.

## Regression tests

The guarantees above are covered in `tests/test_web_mcp.py`, offline, via
injected resolver and connection fakes:

| Test | Guards |
|---|---|
| `test_is_blocked_ip_rejects_non_public` | Address classification, including IPv4-mapped forms |
| `test_assert_fetchable_rejects_when_any_resolved_address_is_private` | Split-horizon DNS answers |
| `test_open_pinned_dials_the_validated_ip_not_the_hostname` | IP pinning / DNS rebinding |
| `test_fetch_revalidates_each_redirect_hop` | Per-hop re-validation |
| `test_fetch_blocks_redirect_to_cloud_metadata_endpoint` | The metadata-endpoint redirect |
| `test_fetch_blocks_relative_redirect_onto_blocked_host` | Protocol-relative redirect targets |
| `test_fetch_gives_up_after_max_redirects` | Redirect-chain bound |
| `test_fetch_enforces_size_cap` | Body size bound |

If you change how fetching works, these are the tests that must keep passing.
