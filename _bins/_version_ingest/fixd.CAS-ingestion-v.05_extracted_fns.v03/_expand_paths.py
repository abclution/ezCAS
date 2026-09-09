def _expand_paths(paths, recursive):
    """Generator that expands paths, skipping symlinks explicitly."""
    for p_str in paths:
        p_raw = Path(p_str)
        
        # 1. Check if argument itself is a symlink
        if p_raw.is_symlink():
            print(f"SKIP (Symlink): {p_raw.name}")
            continue
            
        p = p_raw.resolve()
        
        if p.is_file():
            yield p
        elif p.is_dir() and recursive:
            for sub in p.rglob('*'):
                # 2. Check if recursed file is a symlink
                if sub.is_symlink():
                    # Silent skip or optional log
                    continue
                if sub.is_file():
                    yield sub
        elif p.is_dir() and not recursive:
            print(f"SKIP (Dir): {p.name} (use -r to recurse)")
