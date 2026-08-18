# Review — `feature/add-claude-agents`



## What changed

Adds three Claude Code subagent definitions under `.claude/agents/`.

- **`pm.md`** — product manager. Scopes features against the project's
  single-file / stdlib-plus-`mcp` constraint, and treats anything touching
  `fetch`/`add_feed` as a security-relevant change first. Encodes the rule that
  new features must stay testable without live network access, since that's a
  property of the existing suite worth protecting.
- **`security-reviewer.md`** — audits the narrow but real risk surface:
  `add_feed(url)` makes the server fetch arbitrary agent-supplied URLs. Lists
  the concrete things to check each review (scheme allowlist, resolved-IP
  checks, size cap, timeouts, per-feed exception isolation) and — importantly —
  documents the two **known open gaps** so a future reviewer doesn't mistake
  them for regressions or wave through a fix that only appears to close them:
  DNS rebinding between check and fetch, and redirects not being re-validated.
- **`git-pipeline.md`** — version control and pipeline manager


no <<<<<<< 
