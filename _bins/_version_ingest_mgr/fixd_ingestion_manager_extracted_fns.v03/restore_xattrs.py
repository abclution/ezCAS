def restore_xattrs(filepath: Path, attrs: Dict[str, bytes]) -> None:
    """Restores raw extended attributes to a file."""
    for name, value in attrs.items():
        try:
            os.setxattr(filepath, name, value)
        except (AttributeError, OSError):
            pass
