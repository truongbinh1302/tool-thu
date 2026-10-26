# PyInstaller spec: Tool Thư as a macOS .app (Apple Silicon, onedir).
# Build with packaging/build_mac.sh on a Mac (or the GitHub Actions workflow).
import re
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
VERSION = re.search(r"__version__\s*=\s*'([^']+)'", (ROOT / 'thu' / '__init__.py').read_text(encoding='utf-8')).group(1)
ICON = ROOT / 'packaging' / 'build' / 'ToolThu.icns'

a = Analysis(
    [str(ROOT / 'start.py')],
    pathex=[str(ROOT)],
    datas=[
        (str(ROOT / 'web'), 'web'),
        (str(ROOT / 'examples' / 'demo-seed.json'), 'examples'),
    ],
    hiddenimports=[],
    excludes=['tkinter', 'unittest', 'pydoc', 'test'],
    noarchive=False,
)
pyz = PYZ(a.pure)

# Same as running `python -X utf8 start.py` from source.
options = [('X utf8', None, 'OPTION')]

exe = EXE(
    pyz,
    a.scripts,
    options,
    exclude_binaries=True,
    name='ToolThu',
    console=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    argv_emulation=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name='ToolThu')
app = BUNDLE(
    coll,
    name='Tool Thư.app',
    icon=str(ICON) if ICON.exists() else None,
    bundle_identifier='vn.binh.toolthu',
    version=VERSION,
    info_plist={
        'CFBundleName': 'Tool Thư',
        'CFBundleDisplayName': 'Tool Thư',
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
        'NSHumanReadableCopyright': 'Tool Thư — dùng nội bộ',
    },
)
