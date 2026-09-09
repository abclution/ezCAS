import os
import sys
import hashlib
import json
import argparse
import subprocess
import shutil
import platform
import shlex
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict
CONFIG_FILE = '.CAS-config'
DEFAULT_SIDECAR_SUFFIX = '.known-as'
DEDUP_SCRIPT = 'CAS-dedupActionlist.sh'

def _expand_paths(paths, recursive):
    """Generator that expands paths, skipping symlinks explicitly."""
    for p_str in paths:
        p_raw = Path(p_str)
        if p_raw.is_symlink():
            print(f'SKIP (Symlink): {p_raw.name}')
            continue
        p = p_raw.resolve()
        if p.is_file():
            yield p
        elif p.is_dir() and recursive:
            for sub in p.rglob('*'):
                if sub.is_symlink():
                    continue
                if sub.is_file():
                    yield sub
        elif p.is_dir() and (not recursive):
            print(f'SKIP (Dir): {p.name} (use -r to recurse)')
