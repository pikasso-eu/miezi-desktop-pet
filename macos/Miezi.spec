# -*- mode: python ; coding: utf-8 -*-
# Baut macos/dist/Miezi.app. Aufgerufen von macos/build.sh (von dort im Ordner macos/).
# LSUIElement steht in der Info.plist, damit die Katze kein Dock-Symbol bekommt.
import os

block = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(block, "miezi_mac.py")],
    pathex=[os.path.join(block, "..", "common")],
    binaries=[],
    datas=[],
    hiddenimports=["sprites.orange", "sprites.schwarz"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest", "pydoc_data"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Miezi",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

app = BUNDLE(
    exe,
    name="Miezi.app",
    icon=os.path.join(block, "..", "art", "miezi.icns"),
    bundle_identifier="de.miezi.desktoppet",
    info_plist={
        "LSUIElement": True,               # kein Dock-Symbol, kein Umschalten per Cmd-Tab
        "NSHighResolutionCapable": True,   # Pixelgrafik scharf auf dem Retina-Display
        "NSHumanReadableCopyright": "Miezi Desktop-Pet",
    },
)
