def get_xattrs(filepath: Path) -> Dict[str, str]:
    """Retrieves all extended attributes (includes tags/metadata)."""
    attrs = {}
    try:
        names = os.listxattr(filepath)
        for name in names:
            try:
                # Decode bytes to string for JSON serialization
                val = os.getxattr(filepath, name)
                attrs[name] = val.decode('utf-8', errors='replace')
            except OSError:
                continue
    except (AttributeError, OSError):
        # xattrs not supported or permission denied
        pass
    return attrs
