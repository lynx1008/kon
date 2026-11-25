#!/bin/zsh
set -e
cd "$(dirname "$0")"
export PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache"
rm -rf build dist
mkdir -p build/kon.iconset
.venv/bin/python build_icon.py build/kon-1024.png
for size in 16 32 128 256 512; do
  /usr/bin/sips -z $size $size build/kon-1024.png --out build/kon.iconset/icon_${size}x${size}.png >/dev/null
  /usr/bin/sips -z $((size * 2)) $((size * 2)) build/kon-1024.png --out build/kon.iconset/icon_${size}x${size}@2x.png >/dev/null
done
if ! /usr/bin/iconutil -c icns build/kon.iconset -o build/kon.icns; then
  echo "Warning: iconutil unavailable; building without embedded .icns icon."
  rm -f build/kon.icns
fi
.venv/bin/pyinstaller --noconfirm --clean kon_macos.spec
mkdir -p outputs
rm -f outputs/コン.dmg
hdiutil create -volname コン -srcfolder "dist/コン.app" -ov -format UDZO "outputs/コン.dmg"
echo "Created outputs/コン.dmg"
