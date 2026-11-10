#!/usr/bin/env bash
# Copy the per-tier worker subagents and the validator into a Claude Code agents folder.
# Usage: install_agents.sh [project|user]   (default: project -> ./.claude/agents)
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DEST="./.claude/agents"; [ "$1" = "user" ] && DEST="$HOME/.claude/agents"
mkdir -p "$DEST"; cp "$HERE"/assets/agents/*.md "$DEST"/
echo "Installed $(ls "$HERE"/assets/agents/*.md | wc -l) agents into $DEST. Run /agents to confirm."
