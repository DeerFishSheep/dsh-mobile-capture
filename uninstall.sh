#!/bin/bash
PLIST="$HOME/Library/LaunchAgents/com.mobilecapture.server.plist"
launchctl bootout "gui/$UID" "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"
pkill -f "\.mobilecapture/app/server.py" 2>/dev/null || true
pkill -f "[m]itmdump --listen-host 0.0.0.0" 2>/dev/null || true
rm -rf "$HOME/.mobilecapture"
rm -rf "$HOME/.dsh/skills/mobile-capture"
rm -f "$HOME/.local/bin/cap" "/usr/local/bin/cap" 2>/dev/null || true
echo "已卸载（AGENTS.md 里的那行指针需要手动删除）"
