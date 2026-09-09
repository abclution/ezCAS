    def _get_storage_path(self, file_hash):
        if self.args.shard_depth == 0:
            return self.repo / file_hash
        
        parts = []
        for i in range(self.args.shard_depth):
            start = i * 2
            parts.append(file_hash[start:start+2])
        
        return self.repo.joinpath(*parts) / file_hash
