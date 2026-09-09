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

def main():
    parser = argparse.ArgumentParser(description='Fixd Ingestion Manager: CAS Ingestion with Reflink support.')
    parser.add_argument('path', help='File or Directory to ingest')
    parser.add_argument('--cas-root', type=Path, default=DEFAULT_CAS_ROOT, help=f'Root directory for CAS storage (default: {DEFAULT_CAS_ROOT})')
    parser.add_argument('--algo', default='sha256', choices=hashlib.algorithms_available, help='Hashing algorithm to use (default: sha256)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--dedup-source', action='store_true', help='Overwrite source duplicate with reflink from CAS (Deduplicate in-place).')
    group.add_argument('--delete-dup', action='store_true', help='Delete source file if it exists in CAS.')
    group.add_argument('--move-dup', metavar='DIR', type=Path, help='Move duplicate source files to specified directory.')
    group.add_argument('--mark-dup', metavar='SUFFIX', help='Rename duplicate source files with suffix (e.g., .DELETED).')
    args = parser.parse_args()
    target = Path(args.path)
    if not target.exists():
        print(f'Error: Path not found: {target}')
        sys.exit(1)
    args.cas_root.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        ingest_file(target, args)
    else:
        for root, _, files in os.walk(target):
            for name in files:
                file_path = Path(root) / name
                ingest_file(file_path, args)
