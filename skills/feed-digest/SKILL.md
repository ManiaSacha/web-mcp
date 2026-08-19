---
name: feed-digest
description: Use when the user wants a synthesized summary or research digest built from indexed feeds — e.g. "what's happening in AI this week", "summarize the news on X", "give me a digest of the last 24 hours".
---

# Feed digest

Turns web-mcp's raw tools (`search`, `trending`, `digest`, `recent`) into a synthesized answer for the user, rather than just relaying tool output verbatim.

## Workflow

1. **Scope the question.** If the user gave a topic ("what's new with rocket launches"), use `search(query, max_days=...)` with a query built from their words, not `digest()` — digest is for "what's happening across everything," search is for "what's happening on this topic."
2. **Scope the time window.** Default to 24h for "today"/"this week" style requests map to `hours=168`. If the user doesn't say, ask or default to 24h and say so explicitly in the answer.
3. **Check trending first for broad requests.** For an open-ended "what's happening" ask, call `trending(hours=...)` to see the dominant terms, then `digest(hours=...)` for the grouped article list — use the trending terms to decide what to lead with in your summary rather than just listing feeds in whatever order `digest` returns them.
4. **Synthesize, don't relay.** The tools return markdown lists of links; don't just paste that back as the whole answer. Write 3-6 sentences (or a short set of bullets grouped by theme, not by source feed) that actually say what happened, then include the most relevant links as supporting citations.
5. **Say when there's nothing.** If `digest()`/`search()` come back empty or with "No recent articles," say that plainly — don't pad a non-answer into paragraphs.

## Handling multiple topics

If the user asks about several distinct topics in one digest request, run separate `search()` calls per topic rather than one broad query — TF-IDF search degrades when the query mixes unrelated terms, since it's a bag-of-words match, not semantic disambiguation between topics.

## Freshness

If the last successful refresh for the relevant feeds looks stale (check `source_health()` if the user seems to expect very recent coverage and results look thin), mention that the digest reflects the last successful fetch rather than guaranteeing real-time coverage, and offer to call `refresh()` before re-running the digest.

## What not to do

- Don't fabricate article content beyond what `summary`/`title` provide — the index only has what the feed published, typically a short excerpt. If the user needs the full article, point them to the link rather than inventing detail.
- Don't silently widen the time window to find more results if the requested window came up empty — report the empty result and ask whether to widen it.
