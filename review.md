# Review — `feature/add-claude-agents`

Branched from `main`. Independent of the server code — mergeable in any order
relative to the other branches.

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
- **`git-pipeline.md`** — version control and pipeline manager, written from the
  workflow rules you supplied. Branching strategy, conventional commits, and the
  bi-directional review protocol are carried over as given. I adapted only the
  release section: your original referenced `package.json`, `capacitor.config.ts`,
  and Android Gradle manifests, which don't exist here — this repo's version of
  record is `pyproject.toml` and its pre-commit check is `pytest`. Flagging that
  substitution explicitly in case you wanted the original text verbatim instead.

## Tests

No automated tests — these are agent prompt definitions, not code. Verified only
that the frontmatter parses as valid YAML and each `name`/`description`/`tools`
field is present and well-formed.

## Not done here

No PR opened and nothing merged — that's yours.
