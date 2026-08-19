#!/usr/bin/env python3
"""Validate the Claude Code plugin layout, manifests, and version sync.

Claude Code discovers skills and agents by directory layout and frontmatter,
and a mistake there fails silently at install time — the component simply
doesn't appear. These checks turn that into a loud CI failure instead.

Run:  python scripts/validate_plugin.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # tomllib is 3.11+; the project supports 3.10
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        sys.exit("This script needs Python 3.11+, or `pip install tomli` on 3.10.")

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors: list[str] = []
checks = 0


def check(condition: bool, message: str) -> bool:
    global checks
    checks += 1
    if not condition:
        errors.append(message)
    return condition


def load_json(relative: str) -> dict:
    path = ROOT / relative
    if not path.exists():
        errors.append(f"{relative} is missing")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{relative} is not valid JSON: {exc}")
        return {}


def main() -> int:
    plugin = load_json(".claude-plugin/plugin.json")
    market = load_json(".claude-plugin/marketplace.json")
    mcp = load_json(".mcp.json")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    # -- manifest required fields ------------------------------------------
    check("name" in plugin, "plugin.json: 'name' is required")
    for field in ("name", "owner", "plugins"):
        check(field in market, f"marketplace.json: {field!r} is required")
    check(isinstance(market.get("owner"), dict) and "name" in market.get("owner", {}),
          "marketplace.json: owner.name is required")

    entries = market.get("plugins") or []
    check(bool(entries), "marketplace.json: 'plugins' must list at least one plugin")
    for entry in entries:
        check("name" in entry and "source" in entry,
              f"marketplace.json: plugin entry needs 'name' and 'source': {entry!r}")

    # -- version sync -------------------------------------------------------
    version = project["version"]
    check(plugin.get("version") == version,
          f"plugin.json version {plugin.get('version')!r} != pyproject {version!r}")
    for entry in entries:
        if entry.get("name") == plugin.get("name"):
            check(entry.get("version") == version,
                  f"marketplace.json version {entry.get('version')!r} != pyproject {version!r}")

    source = (ROOT / "web_mcp.py").read_text(encoding="utf-8")
    ua = re.search(r'USER_AGENT = "web-mcp/([\d.]+)"', source)
    check(ua is not None, "web_mcp.py: USER_AGENT not found")
    if ua:
        check(version.startswith(ua.group(1)),
              f"USER_AGENT {ua.group(1)!r} does not match version {version!r}")

    # -- the MCP command must actually be shipped ---------------------------
    scripts = project.get("scripts", {})
    for name, server in (mcp.get("mcpServers") or {}).items():
        command = server.get("command", "")
        check(command in scripts,
              f".mcp.json server {name!r} runs {command!r}, which is not in "
              f"[project.scripts] ({', '.join(scripts) or 'none'}) — plugin "
              f"installs would fail to start the server")

    # -- component layout ---------------------------------------------------
    check((ROOT / "skills").is_dir(), "skills/ must exist at the plugin root")
    check((ROOT / "agents").is_dir(), "agents/ must exist at the plugin root")
    check(not (ROOT / ".claude").exists(),
          ".claude/ exists — components there are invisible to plugin installs")

    components = sorted((ROOT / "skills").glob("*/SKILL.md")) + \
        sorted((ROOT / "agents").glob("*.md"))
    check(bool(components), "no skills or agents found")

    for path in components:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if not check(text.startswith("---"), f"{rel}: missing YAML frontmatter"):
            continue
        frontmatter = text.split("---", 2)[1]
        name = re.search(r"^name:\s*(.+)$", frontmatter, re.M)
        description = re.search(r"^description:\s*(.+)$", frontmatter, re.M)
        if not check(name is not None, f"{rel}: frontmatter has no 'name'"):
            continue
        check(description is not None, f"{rel}: frontmatter has no 'description'")

        expected = path.parent.name if path.name == "SKILL.md" else path.stem
        check(name.group(1).strip() == expected,
              f"{rel}: frontmatter name {name.group(1).strip()!r} must match "
              f"its {'directory' if path.name == 'SKILL.md' else 'filename'} {expected!r}")

    # -- report -------------------------------------------------------------
    if errors:
        print(f"FAILED - {len(errors)} problem(s) across {checks} checks:\n")
        for message in errors:
            print(f"  - {message}")
        return 1

    print(f"OK - {checks} checks passed")
    print(f"   plugin {plugin.get('name')} v{version} in marketplace {market.get('name')}")
    print(f"   install: /plugin install {plugin.get('name')}@{market.get('name')}")
    print(f"   components: {len(components)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
