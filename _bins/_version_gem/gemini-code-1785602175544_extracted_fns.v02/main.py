def main():
    parser = argparse.ArgumentParser(description="ezCAS Storage Utility")
    parser.add_argument("repo", help="Path to CAS Repository")
    parser.add_argument("files", nargs="*", help="Files to ingest")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recursive ingestion"
    )
    parser.add_argument("--algo", choices=["sha256", "sha512"], default="sha256")
    parser.add_argument("--format", choices=["xml", "json"], default="json")
    parser.add_argument("--suffix", default=".known-as")
    parser.add_argument(
        "--link-mode",
        choices=["reflink", "hardlink", "symlink", "copy", "move"],
        default="reflink",
    )
    parser.add_argument(
        "--dedup-mode",
        choices=["ignore", "delete", "hardlink", "softlink"],
        default="ignore",
    )
    parser.add_argument("--shard-depth", type=int, default=1)
    parser.add_argument("--migrate-shards", action="store_true")

    args = parser.parse_args()
    cfg = load_or_init_config(args.repo, args)

    if args.migrate_shards:
        migrate_shards(args.repo, args.shard_depth, cfg["format"], cfg["suffix"])
        cfg["shard_depth"] = args.shard_depth
        atomic_write(os.path.join(args.repo, CONFIG_FILE), json.dumps(cfg, indent=2))
        return

    targets = []
    for f in args.files:
        if os.path.isdir(f) and args.recursive:
            for root, _, filenames in os.walk(f):
                for fn in filenames:
                    targets.append(os.path.join(root, fn))
        elif os.path.isfile(f):
            targets.append(f)

    for target in targets:
        ingest_file(target, args.repo, cfg, args)
