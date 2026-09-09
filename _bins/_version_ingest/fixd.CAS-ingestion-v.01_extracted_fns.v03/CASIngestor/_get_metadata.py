    def _get_metadata(self, filepath):
        stat = os.stat(filepath)
        path_hash = hashlib.sha256(str(filepath.resolve()).encode()).hexdigest()
        meta = {
            "path": str(filepath.resolve()),
            "ingested_at": datetime.now().isoformat(),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "mode": oct(stat.st_mode)[-3:],
            "xattrs": "TODO" 
        }
        return path_hash, meta
