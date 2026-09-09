    def _resolve_config(self, args):
        config_path = self.repo / CONFIG_FILE
        saved_opts = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                saved_opts = json.load(f)
        
        final_ns = argparse.Namespace(**vars(args))
        
        # Priority: Saved Config > Defaults. 
        # (CLI args override this if they differ from default, handled by argparse, 
        # but here we ensure saved config is respected if CLI was left as default)
        if saved_opts:
            for k, v in saved_opts.items():
                if getattr(args, k) == getattr(args_parser.get_default(k), k, None):
                     setattr(final_ns, k, v)

        # Update Config File with current settings (ensures shard_depth is remembered)
        with open(config_path, 'w') as f:
            opts = {k: getattr(final_ns, k) for k in 
                   ['algo', 'use_external', 'format', 'link_mode', 'shard_depth']}
            json.dump(opts, f)
            
        return final_ns
