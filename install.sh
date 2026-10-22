#!/bin/bash
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/.mobilecapture"
PLIST="$HOME/Library/LaunchAgents/com.mobilecapture.server.plist"
SKILL="$HOME/.dsh/skills/mobile-capture"

echo "检查依赖"
if ! command -v mitmdump >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "安装 mitmproxy（首次较慢）"
    brew install mitmproxy >/dev/null 2>&1 || { echo "mitmproxy 安装失败，请手动执行: brew install mitmproxy"; exit 1; }
    find "$(brew --prefix)/Caskroom/mitmproxy" -maxdepth 3 -name "mitmproxy.app" -exec xattr -dr com.apple.quarantine {} \; 2>/dev/null || true
  else
    echo "缺少 Homebrew，请先安装: https://brew.sh"
    exit 1
  fi
fi
command -v mitmdump >/dev/null 2>&1 || { echo "mitmdump 不在 PATH，请确认 /opt/homebrew/bin 已加入"; exit 1; }

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
  <key>Label</key><string>com.mobilecapture.server</string>
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
LINE="- 抓包分析：本地服务 mobile-capture，数据在 ~/.mobilecapture/data/session/，命令 cap（详见 skill mobile-capture）"
touch "$AG"
grep -q "mobile-capture" "$AG" || printf "\n%s\n" "$LINE" >> "$AG"

BIN=/usr/local/bin
[ -w "$BIN" ] || { BIN="$HOME/.local/bin"; mkdir -p "$BIN"; }
ln -sf "$TARGET/app/cap" "$BIN/cap"
echo "命令已安装: $BIN/cap"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "提示: $BIN 不在 PATH，重启终端或自行添加";; esac

sleep 2
IP="$(ipconfig getifaddr en0 2>/dev/null || echo 127.0.0.1)"
echo ""
echo "完成，控制台: http://$IP:8899/"
open "http://$IP:8899/" 2>/dev/null || true
