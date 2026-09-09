    def _GetMetadata(self, filepath):
        stat = os.stat(filepath)
        path_id = hashlib.sha256(str(filepath).encode()).hexdigest()

        xattrs_data = _GetFileXattrs(filepath)

        meta = {
            "path": str(filepath),
            "ingested_at": datetime.now().isoformat(),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "mode": oct(stat.st_mode)[-3:],
            "xattrs": xattrs_data,
        }
        return path_id, meta
