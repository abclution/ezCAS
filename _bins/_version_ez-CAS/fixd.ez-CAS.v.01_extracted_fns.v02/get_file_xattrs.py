def get_file_xattrs(filepath: Path) -> Dict[str, str]:
    attrs = {}
    try:
        names = os.listxattr(filepath, follow_symlinks=False)
        for name in names:
            try:
                val = os.getxattr(filepath, name, follow_symlinks=False)
                attrs[name] = base64.b64encode(val).decode("utf-8")
            except OSError:
                continue
    except (AttributeError, OSError):
        pass
    return attrs
