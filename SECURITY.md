# Security Policy

## Supported versions

web-mcp is pre-1.0. Fixes land on `main` and go out in the next release; older
tags are not patched.

| Version | Supported |
|---|---|
| 0.2.x | ✅ |
| < 0.2 | ❌ |

## Reporting a vulnerability

Report privately through GitHub's
[private vulnerability reporting](https://github.com/ManiaSacha/web-mcp/security/advisories/new)
rather than opening a public issue.

Please include the feed URL or feed body that triggers it, the behavior you
observed, and what you expected. A minimal XML snippet or URL that reproduces
the problem is worth more than a description.

Expect an initial response within 7 days. This is a small, single-maintainer
project — there is no bounty program, and no formal SLA beyond a good-faith
effort to fix real issues promptly and credit reporters who want it.

## Threat model

web-mcp is designed to run **locally, over stdio, for one user's own agent**.
It has no authentication of its own and does not expect to be reachable by
anyone but the agent it was launched by.

The security-relevant surface is narrow but real: `add_feed(url)` makes the
server fetch a URL, and that URL may ultimately originate from something the
agent read rather than from the user. Everything downstream parses bytes from
a remote server that may be hostile.

**In scope**

- Fetching a URL that reaches a host the operator did not intend (SSRF)
- Crashing, hanging, or exhausting memory on hostile feed content
- One malformed feed breaking indexing for unrelated feeds

**Out of scope**

- Exposing the server on a network without adding authentication. It has none;
  don't do this.
- The content of feeds you deliberately added. web-mcp indexes what a feed
  publishes; it does not vet whether that content is true or safe to act on.
  Treat indexed article text as untrusted data, never as instructions.
- Denial of service by an operator against their own instance (adding
  thousands of feeds, a 1-second refresh interval, etc.)

## What is enforced

See [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md) for the full detail,
including the limits that remain.

- **Scheme allowlist** — only `http` and `https`. `file://`, `ftp://`,
  `gopher://`, and `data:` are refused.
- **Public-address requirement** — a URL is refused unless *every* address it
  resolves to is publicly routable. Loopback, RFC1918, link-local (including
  the `169.254.169.254` cloud metadata endpoint), multicast, reserved, and
  unspecified addresses are rejected, as are their IPv4-mapped IPv6 forms.
- **Connect-time IP pinning** — the address that was validated is the address
  actually connected to, closing the DNS-rebinding window between check and
  connect. TLS still validates the certificate against the hostname.
- **Per-hop redirect validation** — redirects are followed manually and every
  hop is re-validated, so a public URL cannot redirect the fetch to an
  internal host. Capped at 5 hops.
- **Resource bounds** — 5 MB cap on a buffered feed body, an explicit socket
  timeout, and a clamp on every tool's `limit` argument.
