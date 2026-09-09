def _expand_paths(paths, recursive):
    for p_str in paths:
        p = Path(p_str).resolve()
        if p.is_file():
            yield p
        elif p.is_dir():
            if recursive:
                for sub in p.rglob('*'):
                    if sub.is_file():
                        yield sub
            else:
                print(f"SKIP (Dir): {p.name} (use -r to recurse)")
