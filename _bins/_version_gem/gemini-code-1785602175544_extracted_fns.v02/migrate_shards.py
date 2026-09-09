def migrate_shards(repo_root, new_depth, fmt, suffix):
    for root, dirs, files in os.walk(repo_root):
        for file in files:
            if file.endswith(suffix) or file == CONFIG_FILE:
                continue
            old_path = os.path.join(root, file)
            file_hash = file
            new_dir = get_shard_dir(repo_root, file_hash, new_depth)
            os.makedirs(new_dir, exist_ok=True)
            new_path = os.path.join(new_dir, file)
            if old_path != new_path:
                set_immutability(old_path, False)
                os.rename(old_path, new_path)
                set_immutability(new_path, True)
                old_sidecar = f"{old_path}{suffix}"
                new_sidecar = f"{new_path}{suffix}"
                if os.path.exists(old_sidecar):
                    os.rename(old_sidecar, new_sidecar)
