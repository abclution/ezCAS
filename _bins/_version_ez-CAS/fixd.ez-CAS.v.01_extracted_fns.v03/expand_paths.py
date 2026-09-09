def expand_paths(paths: list, recursive: bool) -> Generator[Path, None, None]:
    for p_str in paths:
        p = Path(p_str)
        if p.is_symlink():
            continue
        res = p.resolve()
        if res.is_file():
            yield res
        elif res.is_dir() and recursive:
            for sub in res.rglob("*"):
                if not sub.is_symlink() and sub.is_file():
                    yield sub
