"""Identify the code and offline assets that a running server actually loaded."""
import hashlib
from pathlib import Path


def build_id(root=None):
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    digest = hashlib.sha256(str(root).encode('utf-8'))
    files = [root / 'start.py', root / 'examples' / 'demo-seed.json']
    files += list((root / 'thu').glob('*.py'))
    files += [p for p in (root / 'web').rglob('*') if p.is_file()]
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode('utf-8'))
        digest.update(b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()
