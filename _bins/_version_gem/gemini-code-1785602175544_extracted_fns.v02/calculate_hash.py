def calculate_hash(filepath, algo="sha256"):
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()
