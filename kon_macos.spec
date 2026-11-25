# PyInstaller specification for the コン macOS desktop app.
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("webview.platforms")

a = Analysis(
    ["desktop_app_web.py"],
    pathex=["."],
    binaries=[],
    datas=[("templates", "templates"), ("static", "static"), ("assets", "assets")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="コン", debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
app = BUNDLE(exe, name="コン.app", icon=None, bundle_identifier="com.kon.converter")
