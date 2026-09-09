def update_sidecar(
    cas_path: Path, 
    original_path: Path, 
    file_hash: str,
    algo_name: str
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
        "xattrs": get_xattrs(original_path)
    }

    data = {
        "hash": file_hash, 
        "algorithm": algo_name,
        "known_as": {}
    }
    
    if sidecar_path.exists():
        try:
            with open(sidecar_path, 'r') as f:
                existing_data = json.load(f)
                # update root keys if missing, but preserve known_as
                data.update(existing_data)
        except json.JSONDecodeError:
            print(f"  [Warning] Corrupt sidecar found for {file_hash}, resetting.")

    # Key by full string path to allow multiple locations
    data["known_as"][str(original_path.absolute())] = meta

    with open(sidecar_path, 'w') as f:
        json.dump(data, f, indent=2)
