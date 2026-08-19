# Review — `feature/plugin-distribution`

Phase 1 of the structural plan: make web-mcp installable rather than clone-only.

## What changed

**Plugin layout.** `.claude/agents/` → `agents/` and `.claude/skills/` → `skills/`. Claude Code requires component directories at the **plugin root**; anything under `.claude/` is only visible to someone who has cloned this repo and opened Claude Code inside it. Git recorded all five moves as renames, so file history is preserved.

**`research-digest` → `feed-digest`.** Both skills now share the `feed-*` prefix so they read as one product. Frontmatter `name:` updated to match the directory — a mismatch there causes the skill to load under the wrong name.

**`.claude-plugin/plugin.json`** — plugin manifest. Includes a `userConfig.feeds` field, so enabling the plugin prompts for a starting feed list and substitutes it into the server's `--feeds` argument. No manual config editing.

**`.claude-plugin/marketplace.json`** — makes the repo itself an installable marketplace. Marketplace name is `maniasacha-web-mcp` and the plugin is `web-mcp`, giving `/plugin install web-mcp@maniasacha-web-mcp`. Naming them differently avoids the confusing `web-mcp@web-mcp`.

**`.mcp.json`** — registers the `web` MCP server on plugin install, so users get the server *and* the skills and agents in one step.

**`install.sh` / `install.ps1`** — locate a Python ≥3.10, install from the local checkout if present or from GitHub otherwise, verify the `web-mcp` command landed on PATH, and print the exact next command. Both handle the PATH-miss case explicitly, since that's the most common silent failure.

**`.github/workflows/release.yml`** — tag-triggered PyPI publish using Trusted Publishing (OIDC), so no API token is stored in repository secrets. Gated on a job that fails the release if the git tag disagrees with `pyproject.toml`'s version, then runs the tests, builds, and `twine check`s before publishing.

**`pyproject.toml`** — added Python 3.10–3.13 classifiers, `Development Status :: 4 - Beta`, topic classifiers, and `Repository`/`Changelog` URLs. Improves PyPI presentation and search.

**README** — rewrote Install into three labelled paths (plugin / server-only / from source), added a "What's included" table covering the server, both skills, and all three agents, and added example prompts. Also documents that `web-mcp --feeds ...` sitting silently is correct stdio behavior, not a hang — an easy first-run misread.

## Verification

- 25 tests pass (`pytest -q`).
- All three JSON manifests parse, and the required marketplace fields (`name`, `owner.name`, per-plugin `name` + `source`) are present.
- All five skill/agent frontmatter `name:` values match their directory or filename.
- `python -m build` produces both distributions; the wheel's `entry_points.txt` contains `web-mcp = web_mcp:main`, confirming pip creates the `web-mcp` command that `.mcp.json` invokes.
- `twine check` passes on both the wheel and the sdist.

## Scope note — one change you didn't explicitly ask for

The fixed `review.md` at the repo root is replaced with `reviews/<branch-name>.md`, and `agents/git-pipeline.md` is updated to require the per-branch filename.

This was forced: the old rule told every branch to write the same path, which is exactly what produced the add/add conflict on PR #3 and would have produced another on this PR. The stale root `review.md` (which described the already-merged tests branch) is deleted. Revert this part if you'd rather keep the flat file — the rest of the branch does not depend on it.

## Before the first PyPI release

Trusted Publishing needs a one-time setup at <https://pypi.org/manage/account/publishing/> — add a pending publisher for owner `ManiaSacha`, repo `web-mcp`, workflow `release.yml`, environment `pypi`. Until then the publish job fails at the OIDC exchange. The steps are also in a comment at the top of the workflow.

Note the sequencing: `pip install web-mcp` only works once that first release lands. Until then, Option C (from source) in the README is the working path, and the install scripts fall back to `pip install git+https://github.com/ManiaSacha/web-mcp.git`.

## Not in this branch

`ci.yml`, issue and PR templates, `dependabot.yml`, `CODEOWNERS`, `SECURITY.md`, `CHANGELOG.md`, and the `docs/` folder are Phase 2/3. The `feed-triage` skill sketched in the plan is new content, not a move, so it's deferred too.
