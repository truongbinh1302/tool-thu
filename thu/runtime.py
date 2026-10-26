"""Identify the code and offline assets that a running server actually loaded."""
import hashlib
import sys
from pathlib import Path

from . import __version__


def is_frozen():
    """True when running from a packaged app (PyInstaller) instead of source."""
    return bool(getattr(sys, 'frozen', False))


def resource_root():
    """Folder holding web/ and examples/: the bundle when packaged, else the source tree."""
    if is_frozen():
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent)).resolve()
    return Path(__file__).resolve().parents[1]


def build_id(root=None):
    root = Path(root or resource_root()).resolve()
    digest = hashlib.sha256(str(root).encode('utf-8'))
    if is_frozen():
        # Source files are compiled into the app; identify it by version + executable.
        digest.update(__version__.encode('utf-8'))
        files = [Path(sys.executable).resolve()]
    else:
        files = [root / 'start.py']
        files += list((root / 'thu').glob('*.py'))
    files += [root / 'examples' / 'demo-seed.json']
    files += [p for p in (root / 'web').rglob('*') if p.is_file()]
    for path in sorted(set(files)):
        if not path.is_file():
            continue
        try:
            label = path.relative_to(root).as_posix()
        except ValueError:
            label = path.name
        digest.update(label.encode('utf-8'))
        digest.update(b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()
