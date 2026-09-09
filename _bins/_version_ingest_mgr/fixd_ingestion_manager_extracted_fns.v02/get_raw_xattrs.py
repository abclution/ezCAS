def get_raw_xattrs(filepath: Path) -> Dict[str, bytes]:
    """Retrieves raw extended attributes (bytes) for high-fidelity restoration."""
    attrs = {}
    try:
        names = os.listxattr(filepath)
        for name in names:
            try:
                attrs[name] = os.getxattr(filepath, name)
            except OSError:
                continue
    except (AttributeError, OSError):
        pass
    return attrs
