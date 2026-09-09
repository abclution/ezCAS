#!/usr/bin/env python3
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

# Configuration
DEFAULT_CAS_ROOT = Path("./cas_store")
SIDECAR_EXT = ".json"
BLOCK_SIZE = 65536


def get_file_hash(filepath: Path, algo_name: str = "sha256") -> str:
    """Calculates hash of a file using specified algorithm."""
    try:
        hasher = hashlib.new(algo_name)
    except ValueError:
        print(f"Error: Invalid hash algorithm '{algo_name}'", file=sys.stderr)
        return ""

    try:
        with open(filepath, "rb") as f:
            while block := f.read(BLOCK_SIZE):
                hasher.update(block)
        return hasher.hexdigest()
    except OSError as e:
        print(f"Error hashing {filepath}: {e}", file=sys.stderr)
        return ""


def get_xattrs(filepath: Path) -> Dict[str, str]:
    """Retrieves all extended attributes (includes tags/metadata)."""
    attrs = {}
    try:
        names = os.listxattr(filepath)
        for name in names:
            try:
                # Decode bytes to string for JSON serialization
                val = os.getxattr(filepath, name)
                attrs[name] = val.decode("utf-8", errors="replace")
            except OSError:
                continue
    except (AttributeError, OSError):
        # xattrs not supported or permission denied
        pass
    return attrs


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


def restore_xattrs(filepath: Path, attrs: Dict[str, bytes]) -> None:
    """Restores raw extended attributes to a file."""
    for name, value in attrs.items():
        try:
            os.setxattr(filepath, name, value)
        except (AttributeError, OSError):
            pass


def reflink_copy(src: Path, dst: Path) -> bool:
    """Performs a CoW reflink copy. Returns True on success."""
    src = src.resolve()
    dst = dst.resolve()

    # 1. macOS clonefile
    if hasattr(os, "clonefile"):
        try:
            if dst.exists():
                os.unlink(dst)
            os.clonefile(src, dst)
            return True
        except OSError as e:
            print(f"  [Error] clonefile failed: {e}", file=sys.stderr)
            return False

    # 2. Linux ioctl FICLONE (0x40049409)
    if platform.system() == "Linux":
        try:
            FICLONE = 0x40049409
            if dst.exists():
                os.unlink(dst)
            # We must open dst in write mode to create it, then clone
            with open(src, "rb") as s_file, open(dst, "wb") as d_file:
                import fcntl

                fcntl.ioctl(d_file.fileno(), FICLONE, s_file.fileno())
            return True
        except Exception:
            # Fallback to cp command if ioctl fails or fcntl missing
            pass

    # 3. CLI Fallback (cp --reflink=always)
    try:
        if dst.exists():
            os.unlink(dst)
        subprocess.run(
            ["cp", "--reflink=always", str(src), str(dst)],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def update_sidecar(
    cas_path: Path, original_path: Path, file_hash: str, algo_name: str
) -> None:
    """Updates or creates the sidecar JSON with source metadata."""
    sidecar_path = cas_path.with_suffix(SIDECAR_EXT)

    # Gather Metadata
    st = original_path.stat()
    meta = {
        "ingested_at": datetime.now().isoformat(),
        "size": st.st_size,
        "mtime": st.st_mtime,
        "mode": stat.filemode(st.st_mode),
        "xattrs": get_xattrs(original_path),
    }

    data = {"hash": file_hash, "algorithm": algo_name, "known_as": {}}

    if sidecar_path.exists():
        try:
            with open(sidecar_path, "r") as f:
                existing_data = json.load(f)
                # update root keys if missing, but preserve known_as
                data.update(existing_data)
        except json.JSONDecodeError:
            print(f"  [Warning] Corrupt sidecar found for {file_hash}, resetting.")

    # Key by full string path to allow multiple locations
    data["known_as"][str(original_path.absolute())] = meta

    with open(sidecar_path, "w") as f:
        json.dump(data, f, indent=2)


def ingest_file(filepath: Path, args: argparse.Namespace) -> None:
    """Main ingestion logic for a single file."""
    # Strict Symlink Skipping
    if filepath.is_symlink():
        print(f"[Skip] Symlink ignored: {filepath}")
        return

    if not filepath.is_file():
        return

    # Calculate Hash
    f_hash = get_file_hash(filepath, args.algo)
    if not f_hash:
        return

    # Setup CAS paths
    cas_root = args.cas_root
    cas_subdir = cas_root / f_hash[:2]
    cas_subdir.mkdir(parents=True, exist_ok=True)
    cas_file = cas_subdir / f_hash

    # Logic Branch: New vs Duplicate
    if not cas_file.exists():
        print(f"[New] Ingesting: {filepath.name} -> {f_hash[:8]}...")
        if reflink_copy(filepath, cas_file):
            update_sidecar(cas_file, filepath, f_hash, args.algo)
            print("  -> Reflinked to CAS successfully.")
        else:
            print("  -> [Error] Reflink failed. Filesystem may not support CoW.")
    else:
        print(f"[Dup] Exists in CAS: {filepath.name} ({f_hash[:8]})")
        # Always update metadata first (preserves history even if deleted below)
        update_sidecar(cas_file, filepath, f_hash, args.algo)
        print("  -> Sidecar metadata updated.")

        # Duplicate Handling Actions
        if args.dedup_source:
            if filepath.stat().st_ino == cas_file.stat().st_ino:
                print("  -> Already deduplicated (same inode).")
            else:
                print("  -> Overwriting source with CAS reflink (Deduplication)...")
                saved_xattrs = get_raw_xattrs(filepath)
                if reflink_copy(cas_file, filepath):
                    restore_xattrs(filepath, saved_xattrs)
                    print("  -> Source deduplicated and xattrs restored.")
                else:
                    print("  -> [Error] Failed to deduplicate source.")

        elif args.delete_dup:
            try:
                filepath.unlink()
                print(f"  -> Deleted duplicate source: {filepath}")
            except OSError as e:
                print(f"  -> [Error] Failed to delete: {e}", file=sys.stderr)

        elif args.move_dup:
            target_dir = args.move_dup
            target_dir.mkdir(parents=True, exist_ok=True)
            dst = target_dir / filepath.name
            try:
                shutil.move(str(filepath), str(dst))
                print(f"  -> Moved duplicate to: {dst}")
            except OSError as e:
                print(f"  -> [Error] Failed to move: {e}", file=sys.stderr)

        elif args.mark_dup:
            suffix = args.mark_dup
            new_path = filepath.with_name(filepath.name + suffix)
            try:
                filepath.rename(new_path)
                print(f"  -> Renamed duplicate to: {new_path.name}")
            except OSError as e:
                print(f"  -> [Error] Failed to rename: {e}", file=sys.stderr)

        else:
            print("  -> Source file left unchanged.")


def main():
    parser = argparse.ArgumentParser(
        description="Fixd Ingestion Manager: CAS Ingestion with Reflink support."
    )
    parser.add_argument("path", help="File or Directory to ingest")

    # Configuration Options
    parser.add_argument(
        "--cas-root",
        type=Path,
        default=DEFAULT_CAS_ROOT,
        help=f"Root directory for CAS storage (default: {DEFAULT_CAS_ROOT})",
    )
    parser.add_argument(
        "--algo",
        default="sha256",
        choices=hashlib.algorithms_available,
        help="Hashing algorithm to use (default: sha256)",
    )

    # Mutually Exclusive Duplicate Handling Options
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dedup-source",
        action="store_true",
        help="Overwrite source duplicate with reflink from CAS (Deduplicate in-place).",
    )
    group.add_argument(
        "--delete-dup",
        action="store_true",
        help="Delete source file if it exists in CAS.",
    )
    group.add_argument(
        "--move-dup",
        metavar="DIR",
        type=Path,
        help="Move duplicate source files to specified directory.",
    )
    group.add_argument(
        "--mark-dup",
        metavar="SUFFIX",
        help="Rename duplicate source files with suffix (e.g., .DELETED).",
    )

    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"Error: Path not found: {target}")
        sys.exit(1)

    # Ensure CAS Root
    args.cas_root.mkdir(parents=True, exist_ok=True)

    if target.is_file():
        ingest_file(target, args)
    else:
        for root, _, files in os.walk(target):
            for name in files:
                file_path = Path(root) / name
                ingest_file(file_path, args)


if __name__ == "__main__":
    main()
