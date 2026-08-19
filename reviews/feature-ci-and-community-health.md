# Review — `feature/ci-and-community-health`

Phase 3: the maintenance signals. Nothing here changes what the server does at
runtime, with one small exception noted below.

## CI (`.github/workflows/ci.yml`)

Four jobs on push to `main`, on every PR, and on demand:

- **test** — Python 3.10–3.13 on Linux, plus macOS and Windows on 3.12.
  `fail-fast: false` so one version failing still reports the others. The
  non-Linux runners earn their minutes here specifically because `fetch` now
  builds sockets by hand and the install scripts are per-platform.
- **lint** — `ruff check`, with GitHub annotations on the diff.
- **package** — builds, `twine check`s, then **installs the wheel and runs both
  console scripts**. That last step exists because `.mcp.json` invokes the
  `web-mcp` command: a packaging change that dropped the entry point would
  break every plugin install while leaving the tests entirely green.
- **manifests** — runs `scripts/validate_plugin.py`.

## `scripts/validate_plugin.py`

36 checks covering manifest required fields, plugin layout, skill and agent
frontmatter, version sync across all four places the version lives, and that
`.mcp.json`'s command is actually declared in `[project.scripts]`.

The reason this is worth a script rather than a code review habit: these
mistakes fail *silently*. A skill whose frontmatter `name` doesn't match its
directory doesn't error — it just never appears, and you find out later
wondering why the plugin seems to do nothing.

I verified the validator actually fails rather than only passing: setting
`plugin.json` to a bogus version made it exit 1 with a precise message, then I
restored the file.

## Lint, and two real findings

Adding ruff meant making the tree lint-clean, so this branch does touch
`web_mcp.py`. Flagging that explicitly since it goes slightly beyond "CI and
community files". Two findings were substantive:

- **`B023` — `parse_feed` closed over the loop variable `children`.** The
  nested `text_of` was only ever called inside the same iteration, so this was
  latent rather than live, but it is exactly the shape that becomes a real bug
  the moment someone stores or defers the closure. `children` is now bound as a
  default argument.
- **`tomllib` is not available on Python 3.10.** Ruff's import grouping
  surfaced this: with `target-version = "py310"` it classified `tomllib` as
  third-party, because it only entered the stdlib in 3.11. The validator would
  have raised `ImportError` for a contributor on the minimum version we
  advertise. It now falls back to `tomli` and, failing that, exits with a clear
  message instead of a traceback.

Everything else was trivia (import order, `Optional[float]` → `float | None`,
two long lines, `pytest.raises(Exception)` → `pytest.raises(ET.ParseError)`).

Three rules are suppressed deliberately, and the reasoning is in
`pyproject.toml` rather than left implicit:

- `SIM905` — ruff wants the stopword prose block rewritten as a one-line list
  literal of ~120 quoted strings. The suggestion is worse than the code.
- `S314` — suggests swapping `xml.etree` for `defusedxml`. ElementTree does not
  resolve external entities, entity expansion is bounded by `MAX_FETCH_BYTES`,
  and the dependency would break the stdlib-only constraint for no real gain.

`BLE001` and `S110` stay **enabled**, with `# noqa` plus a reason at the two
intentional sites, so a *new* blind except still gets caught. A blanket ignore
would have been less work and strictly worse.

## Community health

- **Issue templates.** Three forms, plus `config.yml` routing security reports
  to private advisories and questions to Discussions, with blank issues off.
  The important one is `feed-compatibility.yml`: it requires the feed URL and
  asks for a single `<item>`/`<entry>` snippet with its parent tag so
  namespaces are visible. That turns the most common bug report directly into
  a test fixture.
- **PR template** with a conditional section for changes touching the fetch
  path, pointing at the security model.
- **`CODEOWNERS`**, **`dependabot.yml`** (pip + actions, weekly), and
  **`.github/release.yml`** so generated release notes group by category.
- **`CHANGELOG.md`** in Keep a Changelog format, backfilled for 0.1.0 and
  0.2.0, with the security fixes under their own heading.
- **`CODE_OF_CONDUCT.md`** (Contributor Covenant 2.1).
- README badges, and `CONTRIBUTING.md` updated — it previously documented only
  `pytest`, which is no longer the whole story.

## Deliberately not included

`CITATION.cff`, which the reference repo ships. Nobody cites a 500-line feed
reader in a paper, and I'd rather not pad the root directory with files that
exist to look thorough. Say the word if you want it anyway.

Coverage reporting is also skipped for now — it needs a Codecov account and a
token, and a coverage badge on a 53-test project mostly measures enthusiasm.

## Verification

Every CI gate was run locally before pushing:

- `pytest` — 53 passed
- `ruff check .` — all checks passed
- `python scripts/validate_plugin.py` — 36 checks passed
- `python -m build` + wheel inspection — both console scripts present
- All 8 YAML files under `.github/` parse

## Note

CI cannot run on this branch until the workflow is merged to `main`; GitHub
will show the checks on the PR itself, which is the first real run.
