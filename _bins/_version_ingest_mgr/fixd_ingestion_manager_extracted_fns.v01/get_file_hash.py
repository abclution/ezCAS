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

def get_file_hash(filepath: Path, algo_name: str='sha256') -> str:
    """Calculates hash of a file using specified algorithm."""
    try:
        hasher = hashlib.new(algo_name)
    except ValueError:
        print(f"Error: Invalid hash algorithm '{algo_name}'", file=sys.stderr)
        return ''
    try:
        with open(filepath, 'rb') as f:
            while (block := f.read(BLOCK_SIZE)):
                hasher.update(block)
        return hasher.hexdigest()
    except OSError as e:
        print(f'Error hashing {filepath}: {e}', file=sys.stderr)
        return ''
