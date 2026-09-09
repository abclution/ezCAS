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

def get_raw_xattrs(filepath: Path) -> Dict[str, bytes]:
    """Retrieves raw extended attributes (bytes) for high-fidelity restoration."""
    attrs = {}
    try:
        names = os.listxattr(filepath)
        for name in names:
            try:
                attrs[name] = os.getxattr(filepath, name)
            except OSError:
                continue
    except (AttributeError, OSError):
        pass
    return attrs
