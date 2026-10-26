#!/bin/bash
# Build "Tool Thư.app" + DMG on an Apple Silicon Mac. Free: ad-hoc signature, no Apple Developer account.
# Usage: bash packaging/build_mac.sh        (from the repo root or anywhere)
set -euo pipefail
cd "$(dirname "$0")/.."

[ "$(uname -s)" = "Darwin" ] || { echo "Cần chạy trên macOS."; exit 1; }
[ "$(uname -m)" = "arm64" ] || echo "Cảnh báo: máy không phải Apple Silicon; spec đang build arm64."

PY=${PYTHON:-python3}
VERSION=$("$PY" -c "import re;print(re.search(r\"__version__\s*=\s*'([^']+)'\",open('thu/__init__.py',encoding='utf-8').read()).group(1))")
APP="dist/Tool Thư.app"
DMG="dist/ToolThu-${VERSION}-mac-arm64.dmg"
echo "== Tool Thư ${VERSION}"

"$PY" -m pip install --upgrade -r packaging/requirements-build.txt
"$PY" -m PyInstaller --version

echo "== Icon"
rm -rf packaging/build dist
ICONSET=packaging/build/ToolThu.iconset
mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z "$s" "$s" packaging/icon-1024.png --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s * 2))
  sips -z "$d" "$d" packaging/icon-1024.png --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o packaging/build/ToolThu.icns

echo "== PyInstaller"
"$PY" -m PyInstaller --noconfirm --clean --distpath dist --workpath packaging/build/work packaging/tool-thu.spec

echo "== Ký ad-hoc (miễn phí)"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

echo "== Chạy thử bản đóng gói"
SMOKE=$(mktemp -d)/"dữ liệu thử"
EXE="$APP/Contents/MacOS/ToolThu"
"$EXE" --no-browser --data-dir "$SMOKE" --port 28901
PORT=$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]))['port'])" "$SMOKE/runtime.json")
curl -fsS --noproxy '*' "http://127.0.0.1:${PORT}/api/health"; echo
curl -fsS --noproxy '*' -o /dev/null "http://127.0.0.1:${PORT}/"
curl -fsS --noproxy '*' "http://127.0.0.1:${PORT}/api/bootstrap" | "$PY" -c "import json,sys;s=json.load(sys.stdin)['state'];assert len(s['teachers'])==20, 'thiếu dữ liệu mẫu';print('Dữ liệu mẫu OK:',len(s['teachers']),'giáo viên')"
"$EXE" --diagnose --data-dir "$SMOKE" | grep '"current": true'
"$EXE" --check-network   # HTTPS tới Google phải xác thực được chứng chỉ trong app đóng gói
"$EXE" --stop --data-dir "$SMOKE"

echo "== DMG"
STAGE=$(mktemp -d)
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/CAI_DAT_MAC.md "$STAGE/Hướng dẫn cài đặt.md"
hdiutil create -volname "Tool Thư ${VERSION}" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
shasum -a 256 "$DMG" | tee "$DMG.sha256"
echo "== Xong: $DMG"
