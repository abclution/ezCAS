def load_or_init_config(repo_root, args):
    os.makedirs(repo_root, exist_ok=True)
    cfg_path = os.path.join(repo_root, CONFIG_FILE)
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg
    cfg = {
        "algo": args.algo,
        "shard_depth": args.shard_depth,
        "format": args.format,
        "suffix": args.suffix,
    }
    atomic_write(cfg_path, json.dumps(cfg, indent=2))
    return cfg
