# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for NatLangChain backend

import sys
import os

block_cipher = None

# Get the source directory
src_dir = os.path.join(SPECPATH, 'src')

a = Analysis(
    [os.path.join(src_dir, 'api.py')],
    pathex=[src_dir],
    binaries=[],
    datas=[
        # Include blockchain data file if exists
        (os.path.join(SPECPATH, 'natlangchain_data.json'), '.')
        if os.path.exists(os.path.join(SPECPATH, 'natlangchain_data.json'))
        else (os.path.join(src_dir, '__init__.py'), 'src'),
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'jinja2',
        'click',
        'itsdangerous',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy ML dependencies for minimal build
        'torch',
        'tensorflow',
        'numpy',
        'scipy',
        'sklearn',
        'sentence_transformers',
        'transformers',
        'anthropic',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='natlangchain-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for debugging; set to False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
