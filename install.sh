#!/usr/bin/env bash
# web-mcp installer (macOS / Linux)
#
# Installs the web-mcp server and prints the next step for wiring it into
# Claude Code. Safe to re-run; it upgrades an existing install in place.
set -euo pipefail

REPO_URL="https://github.com/ManiaSacha/web-mcp"
MIN_MINOR=10

say()  { printf '%s\n' "$*"; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }

# ---- locate a suitable interpreter -------------------------------------------
PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, $MIN_MINOR) else 1)" 2>/dev/null; then
            PY="$candidate"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    fail "Python 3.$MIN_MINOR+ is required but was not found on PATH.
Install it from https://www.python.org/downloads/ and re-run this script."
fi

say "Using $($PY --version) at $(command -v "$PY")"

# ---- install ------------------------------------------------------------------
# Run from a checkout if one is present, otherwise pull straight from GitHub.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    say "Installing from local checkout: $SCRIPT_DIR"
    "$PY" -m pip install --upgrade "$SCRIPT_DIR"
else
    say "Installing from $REPO_URL"
    "$PY" -m pip install --upgrade "git+$REPO_URL.git"
fi

# ---- verify -------------------------------------------------------------------
if ! command -v web-mcp >/dev/null 2>&1; then
    say ""
    say "web-mcp installed, but the 'web-mcp' command is not on your PATH."
    say "pip usually places it in one of these:"
    say "  ~/.local/bin            (Linux, pip --user)"
    say "  ~/Library/Python/3.x/bin (macOS)"
    say "Add the right one to PATH, then re-run this script to verify."
    exit 1
fi

say ""
say "Installed: $(command -v web-mcp)"
say ""
say "Next — pick one:"
say ""
say "  A) Claude Code plugin (also installs the skills and agents):"
say "       /plugin marketplace add ManiaSacha/web-mcp"
say "       /plugin install web-mcp@maniasacha-web-mcp"
say ""
say "  B) MCP server only:"
say "       claude mcp add web -- web-mcp --feeds https://hnrss.org/frontpage"
say ""
say "  C) Claude Desktop — add this to claude_desktop_config.json:"
say '       "web": { "command": "web-mcp", "args": ["--feeds", "https://hnrss.org/frontpage"] }'
