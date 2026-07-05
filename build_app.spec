import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

if sys.platform == "win32":
    ICON_PATH = "assets/icon.ico"
elif sys.platform == "darwin":
    ICON_PATH = "assets/icon.icns"
else:
    ICON_PATH = None

datas, binaries, hiddenimports = collect_all("PySide6")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=["opencv-python"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageCompare",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON_PATH,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="ImageCompare",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ImageCompare.app",
        icon=ICON_PATH,
        bundle_identifier="com.imagecompare.app",
    )
