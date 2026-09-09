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
