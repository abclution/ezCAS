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

def get_xattrs(filepath: Path) -> Dict[str, str]:
    """Retrieves all extended attributes (includes tags/metadata)."""
    attrs = {}
    try:
        names = os.listxattr(filepath)
        for name in names:
            try:
                val = os.getxattr(filepath, name)
                attrs[name] = val.decode('utf-8', errors='replace')
            except OSError:
                continue
    except (AttributeError, OSError):
        pass
    return attrs
