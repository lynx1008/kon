#!/bin/zsh
set -e
cd "$(dirname "$0")"
export PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache"
rm -rf build dist
.venv/bin/pyinstaller --noconfirm --clean kon_macos.spec
mkdir -p outputs
rm -f outputs/コン.dmg
hdiutil create -volname コン -srcfolder "dist/コン.app" -ov -format UDZO "outputs/コン.dmg"
echo "Created outputs/コン.dmg"
