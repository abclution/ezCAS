def migrate_structure(conf: Dict[str, Any]):
    repo = conf["repo"]
    for item in repo.rglob("*"):
        if not item.is_file() or item.name in [CONFIG_FILE, DEDUP_SCRIPT]:
            continue
        f_hash = (
            item.name[: -len(conf["suffix"])]
            if item.name.endswith(conf["suffix"])
            else item.name
        )
        target = get_storage_path(repo, f_hash, conf["shard_depth"])
        if item.name.endswith(conf["suffix"]):
            target = target.parent / (target.name + conf["suffix"])
        if item.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(item, target)
    for root, dirs, _ in os.walk(repo, topdown=False):
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
