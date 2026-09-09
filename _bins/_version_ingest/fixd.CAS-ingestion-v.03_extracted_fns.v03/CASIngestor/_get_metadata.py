    def _get_metadata(self, filepath):
        """Restored helper method."""
        stat = os.stat(filepath)
        path_id = hashlib.sha256(str(filepath).encode()).hexdigest()
        
        meta = {
            "path": str(filepath),
            "ingested_at": datetime.now().isoformat(),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "mode": oct(stat.st_mode)[-3:],
            "xattrs": "TODO" 
        }
        return path_id, meta
