---
name: feed-curation
description: Use when the user wants to add, remove, prune, or evaluate RSS/Atom feeds for a web-mcp instance — e.g. "add some good AI news feeds", "check if any of my feeds are dead", "this feed is too noisy, replace it".
---

# Feed curation

Helps a user build and maintain a healthy set of feeds in a running web-mcp server.

## Adding feeds

1. Ask what topic(s) or sources the user wants covered, if not already clear.
2. Prefer well-known, stable RSS/Atom endpoints (a project's own `/feed/` or `/rss` path, not a third-party aggregator scraping it) — these are less likely to disappear or change shape.
3. Call the `add_feed` tool for each candidate URL and read its response — it reports how many articles were indexed, or a fetch/parse error. Zero articles indexed is worth flagging to the user even if the call "succeeded": it usually means the URL isn't actually a feed, or is empty.
4. If `add_feed` fails, read the error message before retrying — it will say if the URL was rejected for scheme/host reasons (`assert_fetchable`) or failed to parse as XML. Don't just retry blindly; confirm the URL actually points at a feed (open it in a browser check, or ask the user) before trying alternates.

## Auditing existing feeds

1. Call `source_health()` and read it feed-by-feed. Statuses:
   - `OK` — fine, no action needed.
   - `WARN` — no successful refresh in >24h. Worth a mention, not necessarily removal.
   - `SILENT` — no successful refresh in >7 days. Likely dead or moved; recommend removal or check for a replacement URL.
   - `ERROR` — currently failing; read the attached error text and explain what it means in plain terms (fetch timeout, non-200, XML parse failure, SSRF rejection because the URL is misconfigured, etc).
2. Call `list_feeds()` for article counts. A feed with a suspiciously low count relative to others might be under-indexed rather than genuinely low-volume — a `refresh()` call can confirm.

## Pruning noisy feeds

If the user says a feed is too noisy (dominating `recent()`/`digest()` output), use `trending()` and `digest()` to show what it's contributing, confirm with the user which feed is the source, then `remove_feed(url)`. Removal is immediate and drops that feed's already-indexed articles too — mention that before doing it, since it's not trivially reversible without re-adding and re-fetching.

## What not to do

- Don't add a large batch of feeds without checking in — a handful at a time, confirmed working via `add_feed`'s response, is more useful than a dozen blind adds where some silently fail.
- Don't recommend feed URLs you're inferring/guessing rather than ones the user gave you or that you've confirmed are real. A wrong guess just produces an `add_feed` error and wastes a round trip.
