def get_metadata(filepath: Path) -> tuple[str, Dict[str, Any]]:
    stat = filepath.stat()
    path_id = hashlib.sha256(str(filepath).encode()).hexdigest()
    meta = {
        "path": str(filepath),
        "processed_at": datetime.now().isoformat(),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mode": oct(stat.st_mode)[-3:],
        "xattrs": get_file_xattrs(filepath),
    }
    return path_id, meta
