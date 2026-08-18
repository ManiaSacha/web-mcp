# web-mcp

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

```bash
pip install web-mcp
```

Or run directly from source:

```bash
git clone https://github.com/ManiaSacha/web-mcp.git
cd web-mcp
pip install -e .
```

## Quick start

Run the server with a starting set of feeds:

```bash
python web_mcp.py --feeds https://hnrss.org/frontpage,https://github.blog/feed/
```

### Use with Claude Code / Claude Desktop

Add it as an MCP server, e.g. in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "web": {
      "command": "python",
      "args": ["/absolute/path/to/web_mcp.py", "--feeds", "https://hnrss.org/frontpage"]
    }
  }
}
```

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

- Only `http://` and `https://` feed URLs are accepted.
- Before fetching, the target hostname is resolved and rejected if it points at a loopback, private, link-local, multicast, or otherwise non-public address — this blocks a compromised or careless `add_feed` call from being used to probe your local network or cloud metadata endpoints (SSRF). This is a best-effort guard, not a sandbox: see the docstring on `assert_fetchable` in [web_mcp.py](web_mcp.py) for its known limitation (DNS can change between the check and the fetch).
- Fetched feed bodies are capped at 5 MB to bound memory use from a hostile or misbehaving feed.
- This server is meant to run **locally**, over stdio, for your own agent. It has no auth of its own — don't expose it over a network without adding some.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
