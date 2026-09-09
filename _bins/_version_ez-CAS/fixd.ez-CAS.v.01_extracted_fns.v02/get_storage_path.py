def get_storage_path(repo: Path, file_hash: str, depth: int) -> Path:
    if depth == 0:
        return repo / file_hash
    parts = [file_hash[i * 2:i * 2 + 2] for i in range(depth)]
    return repo.joinpath(*parts) / file_hash
