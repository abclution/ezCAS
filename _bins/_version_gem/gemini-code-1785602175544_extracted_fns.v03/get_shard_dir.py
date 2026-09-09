def get_shard_dir(repo_root, file_hash, shard_depth):
    depth = max(0, min(shard_depth, len(file_hash) // 2))
    path_components = [file_hash[i * 2 : i * 2 + 2] for i in range(depth)]
    return os.path.join(repo_root, *path_components)
