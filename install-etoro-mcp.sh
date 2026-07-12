#!/bin/bash
# eToro MCP installer for Claude Code.
# Creates the venv, installs deps, and writes a project-scoped .mcp.json
# (Claude Code's default project MCP config path) in the project root.
set -e

# Resolve paths relative to this script, so they stay correct if the folder moves.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="$PROJECT_DIR/etoro-mcp"
CONFIG="$PROJECT_DIR/.mcp.json"

echo "[1/3] Creating venv + installing dependencies..."
# --clear rebuilds launcher scripts too: a venv copied from another folder has
# pip wrappers whose shebangs still point at the old path.
python3 -m venv --clear "$MCP_DIR/.venv"
"$MCP_DIR/.venv/bin/python3" -m pip install --quiet --upgrade pip
"$MCP_DIR/.venv/bin/python3" -m pip install --quiet -r "$MCP_DIR/requirements.txt"

echo "[2/3] Enter your eToro API keys (demo environment, input hidden):"
read -r -s -p "  Public API Key: " ETORO_API_KEY; echo
read -r -s -p "  User Key (Demo): " ETORO_USER_KEY; echo

echo "[3/3] Writing $CONFIG (backup saved as .bak if it exists)..."
[ -f "$CONFIG" ] && cp "$CONFIG" "$CONFIG.bak"

export ETORO_API_KEY ETORO_USER_KEY MCP_DIR CONFIG
python3 <<'EOF'
import json, os

cfg_path = os.environ["CONFIG"]
mcp_dir = os.environ["MCP_DIR"]

try:
    with open(cfg_path) as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}

cfg.setdefault("mcpServers", {})["etoro"] = {
    "type": "stdio",
    "command": f"{mcp_dir}/.venv/bin/python3",
    "args": [f"{mcp_dir}/server.py"],
    "env": {
        "ETORO_API_KEY": os.environ["ETORO_API_KEY"],
        "ETORO_USER_KEY": os.environ["ETORO_USER_KEY"],
        "ETORO_MODE": "demo",
        "ETORO_ENABLE_TRADING": "false",
    },
}

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")

print("  etoro server written to .mcp.json. Existing entries preserved.")
EOF

echo "Done. Start Claude Code in this folder ('claude') and check with /mcp."
echo "Note: .mcp.json contains your keys — it is gitignored; keep it that way."
