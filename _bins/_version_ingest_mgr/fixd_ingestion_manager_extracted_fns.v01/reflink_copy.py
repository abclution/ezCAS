import os
import sys
import hashlib
import json
import argparse
import platform
import subprocess
import stat
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
DEFAULT_CAS_ROOT = Path('./cas_store')
SIDECAR_EXT = '.json'
BLOCK_SIZE = 65536

def reflink_copy(src: Path, dst: Path) -> bool:
    """Performs a CoW reflink copy. Returns True on success."""
    src = src.resolve()
    dst = dst.resolve()
    if hasattr(os, 'clonefile'):
        try:
            if dst.exists():
                os.unlink(dst)
            os.clonefile(src, dst)
            return True
        except OSError as e:
            print(f'  [Error] clonefile failed: {e}', file=sys.stderr)
            return False
    if platform.system() == 'Linux':
        try:
            FICLONE = 1074041865
            if dst.exists():
                os.unlink(dst)
            with open(src, 'rb') as s_file, open(dst, 'wb') as d_file:
                import fcntl
                fcntl.ioctl(d_file.fileno(), FICLONE, s_file.fileno())
            return True
        except Exception:
            pass
    try:
        if dst.exists():
            os.unlink(dst)
        subprocess.run(['cp', '--reflink=always', str(src), str(dst)], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
