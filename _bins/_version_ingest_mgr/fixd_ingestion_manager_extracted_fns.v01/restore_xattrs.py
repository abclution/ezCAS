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

def restore_xattrs(filepath: Path, attrs: Dict[str, bytes]) -> None:
    """Restores raw extended attributes to a file."""
    for name, value in attrs.items():
        try:
            os.setxattr(filepath, name, value)
        except (AttributeError, OSError):
            pass
