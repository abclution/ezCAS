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

def ingest_file(filepath: Path, args: argparse.Namespace) -> None:
    """Main ingestion logic for a single file."""
    if filepath.is_symlink():
        print(f'[Skip] Symlink ignored: {filepath}')
        return
    if not filepath.is_file():
        return
    f_hash = get_file_hash(filepath, args.algo)
    if not f_hash:
        return
    cas_root = args.cas_root
    cas_subdir = cas_root / f_hash[:2]
    cas_subdir.mkdir(parents=True, exist_ok=True)
    cas_file = cas_subdir / f_hash
    if not cas_file.exists():
        print(f'[New] Ingesting: {filepath.name} -> {f_hash[:8]}...')
        if reflink_copy(filepath, cas_file):
            update_sidecar(cas_file, filepath, f_hash, args.algo)
            print('  -> Reflinked to CAS successfully.')
        else:
            print('  -> [Error] Reflink failed. Filesystem may not support CoW.')
    else:
        print(f'[Dup] Exists in CAS: {filepath.name} ({f_hash[:8]})')
        update_sidecar(cas_file, filepath, f_hash, args.algo)
        print('  -> Sidecar metadata updated.')
        if args.dedup_source:
            if filepath.stat().st_ino == cas_file.stat().st_ino:
                print('  -> Already deduplicated (same inode).')
            else:
                print('  -> Overwriting source with CAS reflink (Deduplication)...')
                saved_xattrs = get_raw_xattrs(filepath)
                if reflink_copy(cas_file, filepath):
                    restore_xattrs(filepath, saved_xattrs)
                    print('  -> Source deduplicated and xattrs restored.')
                else:
                    print('  -> [Error] Failed to deduplicate source.')
        elif args.delete_dup:
            try:
                filepath.unlink()
                print(f'  -> Deleted duplicate source: {filepath}')
            except OSError as e:
                print(f'  -> [Error] Failed to delete: {e}', file=sys.stderr)
        elif args.move_dup:
            target_dir = args.move_dup
            target_dir.mkdir(parents=True, exist_ok=True)
            dst = target_dir / filepath.name
            try:
                shutil.move(str(filepath), str(dst))
                print(f'  -> Moved duplicate to: {dst}')
            except OSError as e:
                print(f'  -> [Error] Failed to move: {e}', file=sys.stderr)
        elif args.mark_dup:
            suffix = args.mark_dup
            new_path = filepath.with_name(filepath.name + suffix)
            try:
                filepath.rename(new_path)
                print(f'  -> Renamed duplicate to: {new_path.name}')
            except OSError as e:
                print(f'  -> [Error] Failed to rename: {e}', file=sys.stderr)
        else:
            print('  -> Source file left unchanged.')
