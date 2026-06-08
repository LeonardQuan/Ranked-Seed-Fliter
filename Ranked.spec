# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Ranked.py'],
    pathex=[],
    binaries=[],
    datas=[('RANKED.png', '.'), ('assets', 'assets')],
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32', 'queue', 'json', 'threading',
                   'constants', 'api_client', 'task_runner', 'gui_app'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Ranked',
    icon='123.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
