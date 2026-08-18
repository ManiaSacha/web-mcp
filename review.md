# Review — `feature/add-claude-skills`

Branched from `main`. Independent of the server code — mergeable in any order
relative to the other branches.

## What changed

Adds two Claude Code skills under `.claude/skills/`.

- **`feed-curation/SKILL.md`** — adding, auditing, and pruning feeds on a
  running instance. Covers reading `add_feed`'s response properly (zero articles
  indexed is a *failure signal* even though the call succeeded), interpreting
  each `source_health` status, and the fact that `remove_feed` also drops
  already-indexed articles, so it should be confirmed with the user first rather
  than treated as trivially reversible.
- **`research-digest/SKILL.md`** — turning the raw tools into a synthesized
  answer. The main rules it encodes: use `search` for topic questions and
  `digest` for open-ended ones, synthesize rather than pasting tool output back
  verbatim, run separate `search` calls per topic (TF-IDF is bag-of-words and
  degrades when a query mixes unrelated terms), don't invent article detail
  beyond the summary the feed actually published, and don't silently widen an
  empty time window.

Both skills include an explicit "what not to do" section, since the failure
modes here are mostly over-eagerness — batch-adding unverified feed URLs, or
padding a genuinely empty result into prose.


no <<<<<<<
