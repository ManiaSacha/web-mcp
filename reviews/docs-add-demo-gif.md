# Review — `docs/add-demo-gif`

Single-commit docs branch. Adds `public/web-mcp.gif` and references it near
the top of the README, right after the intro paragraph and before the
features list — the first thing a visitor sees.

## What changed

- `public/web-mcp.gif` (483 KB) — the demo recording, added as a tracked binary.
- `README.md` — one line, `![web-mcp demo](public/web-mcp.gif)`.

Both are in the same commit deliberately: a README pointing at an untracked
image is a broken reference the moment anyone else clones the repo, so the
asset and the line referencing it are one logical change, not two.

## Tests

`pytest -q` — 53 passed. (A docs-only change; ran the suite anyway since the
pipeline rule asks for it before every review handoff, not conditionally.)

## Known limitations / follow-up

None. This doesn't touch `web_mcp.py`, so `ruff` and
`scripts/validate_plugin.py` are unaffected — not re-run here as they don't
exercise anything this commit touches.
