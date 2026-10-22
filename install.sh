#!/bin/bash
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/.ioscapture"
PLIST="$HOME/Library/LaunchAgents/com.ioscapture.server.plist"
SKILL="$HOME/.dsh/skills/ios-capture"

echo "安装到 $TARGET"
mkdir -p "$TARGET/app" "$TARGET/data" "$TARGET/logs"
cp "$SRC/app/"* "$TARGET/app/"
chmod +x "$TARGET/app/cap"

PY=/opt/homebrew/bin/python3
[ -x "$PY" ] || PY=$(command -v python3)
echo "准备运行环境"
[ -d "$TARGET/venv" ] || "$PY" -m venv "$TARGET/venv"
"$TARGET/venv/bin/pip" -q install --upgrade pip >/dev/null 2>&1 || true
"$TARGET/venv/bin/pip" -q install qrcode pillow >/dev/null

echo "注册开机启动"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.ioscapture.server</string>
  <key>ProgramArguments</key><array>
    <string>$TARGET/venv/bin/python</string>
    <string>$TARGET/app/server.py</string>
  </array>
  <key>WorkingDirectory</key><string>$TARGET/app</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
  <key>StandardOutPath</key><string>$TARGET/logs/server.log</string>
  <key>StandardErrorPath</key><string>$TARGET/logs/server.log</string>
</dict></plist>
EOF
launchctl bootout "gui/$UID" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID" "$PLIST" || true

echo "安装技能"
mkdir -p "$SKILL"
cp "$SRC/skill/SKILL.md" "$SKILL/SKILL.md"

AG="$HOME/.dsh/AGENTS.md"
LINE="- 抓包分析：本地服务 ios-capture，数据在 ~/.ioscapture/data/session/，命令 cap（详见 skill ios-capture）"
touch "$AG"
grep -q "ios-capture" "$AG" || printf "\n%s\n" "$LINE" >> "$AG"

BIN=/usr/local/bin
[ -w "$BIN" ] || { BIN="$HOME/.local/bin"; mkdir -p "$BIN"; }
ln -sf "$TARGET/app/cap" "$BIN/cap"
echo "命令已安装: $BIN/cap"

sleep 2
IP="$(ipconfig getifaddr en0 2>/dev/null || echo 127.0.0.1)"
echo ""
echo "完成，控制台: http://$IP:8899/"
open "http://$IP:8899/" 2>/dev/null || true
