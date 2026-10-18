#!/usr/bin/python3
"""Refresh checksums after intentional changes to the repository payload."""
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = sorted(path for path in root.rglob('*') if path.is_file() and not path.is_symlink()
               and not {'.git', '__pycache__', '.pytest_cache'}.intersection(path.relative_to(root).parts)
               and path.name != 'SHA256SUMS' and path.suffix not in {'.pyc', '.log'})
lines = [f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}\n'
         for path in paths]
(root / 'SHA256SUMS').write_text(''.join(lines))
print(f'{len(lines)} archivos registrados en SHA256SUMS')
