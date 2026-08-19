# web-mcp

[![ci](https://github.com/ManiaSacha/web-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/ManiaSacha/web-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/feed-mcp.svg)](https://pypi.org/project/feed-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/feed-mcp.svg)](https://pypi.org/project/feed-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Semantic search over RSS/Atom feeds for AI agents — a single-file [MCP](https://modelcontextprotocol.io) server. No API key, no cloud, just the feeds you choose.

Point it at a handful of RSS/Atom feeds and give an agent tools to search them by meaning (TF-IDF + recency boost), see what's trending, generate a digest, and monitor feed health — all running locally against feeds you control.

## Features

- **Add/remove/list feeds** — RSS 2.0 and Atom
- **Ranked search** — TF-IDF cosine similarity with a recency boost, pure stdlib (no embeddings, no network calls beyond fetching the feeds themselves)
- **Trending topics** — most frequent terms across recent articles
- **Source health** — flags feeds that are erroring, silent, or stale
- **Markdown digests** — grouped-by-feed summary of recent articles
- **Background refresh** — feeds are refreshed on a timer automatically

## Install

Requires Python 3.10+.

> **On the package name:** the project is `web-mcp`, but the PyPI distribution is **`feed-mcp`** — PyPI rejects `web-mcp` as too similar to an unrelated existing `webmcp` package. So you `pip install feed-mcp`, and it installs both a `web-mcp` and a `feed-mcp` command; they're the same program, use whichever you prefer.

### Option A — Claude Code plugin (recommended)

Installs the MCP server **and** the bundled skills and agents in one step:

```bash
pip install feed-mcp
```

Then, inside Claude Code:

```
/plugin marketplace add ManiaSacha/web-mcp
/plugin install web-mcp@maniasacha-web-mcp
```

The plugin registers the `web` MCP server automatically and prompts you for a starting feed list. If the install summary says `Run /reload-plugins to activate.`, run that.

> The `pip install` step is required: the plugin's MCP server invokes the `web-mcp` command, which pip puts on your PATH.

### Option B — MCP server only

```bash
pip install feed-mcp
claude mcp add web -- web-mcp --feeds https://hnrss.org/frontpage
```

For **Claude Desktop**, add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "web": {
      "command": "web-mcp",
      "args": ["--feeds", "https://hnrss.org/frontpage,https://github.blog/feed/"]
    }
  }
}
```

### Option C — from source

```bash
git clone https://github.com/ManiaSacha/web-mcp.git
cd web-mcp
./install.sh          # Windows: .\install.ps1
```

The install scripts check your Python version, install the package, and print the exact next command for your setup.

## Quick start

Run the server directly to check it works:

```bash
web-mcp --feeds https://hnrss.org/frontpage,https://github.blog/feed/
```

It speaks MCP over stdio, so it will sit silently waiting for a client — that's correct behavior, not a hang. Press Ctrl+C to exit.

Once connected, ask your agent things like:

- *"What's trending across my feeds today?"*
- *"Search my feeds for anything about Postgres performance."*
- *"Give me a digest of the last 24 hours."*
- *"Are any of my feeds broken?"*

## What's included

| Component | Name | Purpose |
|---|---|---|
| MCP server | `web` | The 9 tools below |
| Skill | `feed-curation` | Add, audit, and prune feeds |
| Skill | `feed-digest` | Turn raw tool output into a synthesized brief |
| Agent | `pm` | Scopes features against the single-file philosophy |
| Agent | `security-reviewer` | Audits the SSRF/fetch surface |
| Agent | `git-pipeline` | Branching, commits, and review handoff |

## Tools

| Tool | Description |
|---|---|
| `add_feed(url)` | Add an RSS/Atom feed and index its current articles |
| `remove_feed(url)` | Remove a feed and its indexed articles |
| `list_feeds()` | List configured feeds with article counts |
| `search(query, limit=10, max_days=30)` | Recency-boosted ranked search |
| `recent(limit=20)` | Most recent articles across all feeds |
| `trending(hours=24, limit=10)` | Trending terms in the last N hours |
| `digest(hours=24, limit=8)` | Markdown digest grouped by feed |
| `source_health()` | Which feeds are healthy, late, or erroring |
| `refresh()` | Force-refresh all feeds immediately |

## Security notes

`add_feed(url)` makes the server fetch a URL that may have reached your agent from a web page rather than from you, so that path is treated as untrusted:

- **Scheme allowlist** — only `http://` and `https://`. `file://`, `ftp://`, `gopher://`, and `data:` are refused.
- **Public addresses only** — a URL is rejected unless *every* address it resolves to is publicly routable. Loopback, private, link-local (including the `169.254.169.254` cloud metadata endpoint), multicast, and reserved addresses are blocked, as are their IPv4-mapped IPv6 forms.
- **Connect-time IP pinning** — the address that was validated is the one actually dialed, so DNS cannot answer differently between the check and the connection (rebinding). TLS still validates certificates against the hostname.
- **Per-hop redirect validation** — redirects are followed manually and re-validated at every hop, so a public URL cannot bounce the fetch to an internal host. Capped at 5 hops.
- **Resource bounds** — 5 MB per feed body, an explicit socket timeout, and a clamp on every tool's `limit`.

Two things this does *not* do: it has **no authentication** (it's meant to run locally over stdio — don't expose it on a network), and it does not vet feed content. Indexed article text is written by whoever controls the feed, so treat it as data, never as instructions.

Full detail, including the limits that remain, is in [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md). To report a vulnerability, see [SECURITY.md](SECURITY.md).

## Development

```bash
pip install -e ".[dev]"
pytest              # 53 tests, no network access
ruff check .        # lint
python scripts/validate_plugin.py   # manifests, frontmatter, version sync
```

CI runs all three on Python 3.10–3.13 (Linux, plus macOS and Windows on 3.12), and additionally installs the built wheel to confirm the console scripts work.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and [CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT
