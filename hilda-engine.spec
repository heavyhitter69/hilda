# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect hidden imports required by various packages (Whisper, Langchain, PyAutoGUI, Playwright, etc.)
hidden_imports = []
hidden_imports += collect_submodules('langchain')
hidden_imports += collect_submodules('langchain_community')
hidden_imports += collect_submodules('langchain_openai')
hidden_imports += collect_submodules('tiktoken')
hidden_imports += collect_submodules('core')
hidden_imports += collect_submodules('plugins')
hidden_imports += [
    'whisper', 'sounddevice', 'numpy', 'websockets', 'websockets.legacy', 
    'websockets.legacy.server', 'colorlog', 'webrtcvad', 'playwright', 
    'pyautogui', 'mss', 'psutil', 'screen_brightness_control'
]

# Collect data files (models, configs, templates)
datas = [
    ('.env.example', '.'),
    ('README.md', '.'),
]

# Specifically collect Whisper assets if needed
datas += collect_data_files('whisper')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='hilda-engine',
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
    icon='ui/build/icon.png'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='hilda-engine',
)
