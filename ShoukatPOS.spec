# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for Shoukat Sons Garments POS.

CRITICAL: Uses --onedir mode, NOT --onefile.
PyInstaller's --onefile mode is disproportionately likely to be flagged
as a trojan by Windows Defender and other AV engines because the bootloader
binary has ended up on AV threat-signature lists after being reused by
actual malware authors.

Build command:
    pyinstaller ShoukatPOS.spec

Or alternatively:
    pyinstaller --noconfirm --windowed --onedir --icon=assets/logo.ico main.py
"""

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from pathlib import Path

# Project root directory
project_root = Path(__file__).parent.resolve()

# Analysis configuration
a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('shoukat_pos/assets', 'assets'),
        ('shoukat_pos/data', 'data'),
        ('shoukat_pos/migrations', 'migrations'),
    ],
    hiddenimports=[
        'customtkinter',
        'tksheet',
        'PIL',
        'PIL._imagingtk',
        'PIL._tkinter_finder',
        'bcrypt',
        'matplotlib.backends.backend_tkagg',
        'sqlalchemy.ext.baked',
        'alembic.runtime.migration',
        'alembic.script',
        'alembic.config',
        'escpos',
        'escpos.printer',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'matplotlib.tests',
        'numpy.random._examples',
        'pytest',
        'pylint',
        'mypy',
        'ruff',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

# Create PYZ archive
pyz = PYZ(a.pure, a.zipped_data)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ShoukatPOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed application, no console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,  # Set this if you have a code signing certificate
    entitlements_file=None,
    icon='shoukat_pos/assets/logo.ico',
)

# Collect into distribution directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ShoukatPOS',
)
