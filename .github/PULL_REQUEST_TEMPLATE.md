<!--
Thanks for contributing. Keep the description focused on *why* — the diff
already shows what changed.
-->

## What and why

<!-- One or two sentences. Link the issue this closes, if any. -->

Closes #

## Checklist

- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] Tests added or updated for the behavior change
- [ ] Any new test works offline (no network calls)

## If this touches fetching

<!-- Delete this section if it doesn't. -->

Changes to `fetch`, `assert_fetchable`, `open_pinned`, or redirect handling are
security-relevant. See [docs/SECURITY-MODEL.md](../blob/main/docs/SECURITY-MODEL.md).

- [ ] Every network fetch still goes through `assert_fetchable`
- [ ] The connection still dials the validated IP rather than re-resolving the hostname
- [ ] Redirects are still followed manually and re-validated per hop
- [ ] The relevant regression tests still pass, and I didn't loosen them

## If this changes the version

- [ ] `pyproject.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
      and `USER_AGENT` all agree (`python scripts/validate_plugin.py`)
- [ ] `CHANGELOG.md` has an entry
