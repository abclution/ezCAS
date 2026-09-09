def get_raw_xattrs(filepath: Path) -> Dict[str, str]:
    """Retrieves raw xattrs and returns them as Base64 encoded strings."""
    attrs = {}
    try:
        # os.listxattr is available on Linux & macOS (Python 3.3+)
        # On some Linux variations, we might need follow_symlinks=False if handling symlinks directly
        names = os.listxattr(filepath, follow_symlinks=False) 
        for name in names:
            try:
                # Get raw bytes
                val = os.getxattr(filepath, name, follow_symlinks=False)
                # Store as Base64 string for safe JSON/XML serialization
                attrs[name] = base64.b64encode(val).decode('utf-8')
            except OSError:
                continue
    except (AttributeError, OSError):
        # Filesystem doesn't support xattrs or permission denied
        pass
    return attrs
