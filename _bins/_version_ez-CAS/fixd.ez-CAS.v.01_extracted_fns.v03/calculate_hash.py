def calculate_hash(filepath: Path, algo: str, use_external: bool) -> str:
    if use_external:
        cmd = f"{algo}sum"
        res = subprocess.check_output([cmd, str(filepath)]).decode().strip()
        return res.split()[0]

    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()
