    def _resolve_config(self, args):
        config_path = self.repo / CONFIG_FILE
        saved_opts = {}
        if config_path.exists():
            with open(config_path, "r") as f:
                saved_opts = json.load(f)

        final_ns = argparse.Namespace(**vars(args))

        if saved_opts:
            for k, v in saved_opts.items():
                if getattr(args, k) == getattr(args_parser.get_default(k), k, None):
                    setattr(final_ns, k, v)

        with open(config_path, "w") as f:
            opts = {
                k: getattr(final_ns, k)
                for k in [
                    "algo",
                    "use_external",
                    "format",
                    "ingest_method",
                    "dedupe_action",
                    "shard_depth",
                ]
            }
            json.dump(opts, f)

        return final_ns
