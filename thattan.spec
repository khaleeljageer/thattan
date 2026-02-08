# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Thattan (Tamil99 Typing Master)
# Build: pyinstaller thattan.spec

import sys
from pathlib import Path

block_cipher = None

# Base path for the thattan package (assets, data)
thattan_dir = Path('thattan')
assets_dir = thattan_dir / 'assets'
data_dir = thattan_dir / 'data'

# Data files for bundling (assets, levels)
datas = [
    (str(assets_dir), 'thattan/assets'),
    (str(data_dir), 'thattan/data'),
]

# Hidden imports for PySide6 and YAML
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    'yaml',
]

# Run from project root: pyinstaller thattan.spec
a = Analysis(
    ['thattan/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# On Windows we want onefile exe; on Linux we use onedir for AppImage
if sys.platform == 'win32':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='Thattan',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window for GUI app
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,  # Add .ico path for Windows icon if desired
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Thattan',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Thattan',
    )
