def extract_xattrs(filepath):
    xattrs = {}
    if not hasattr(os, "listxattr"):
        return xattrs
    try:
        attrs = os.listxattr(filepath)
        for attr in attrs:
            try:
                val = os.getxattr(filepath, attr)
                xattrs[attr] = base64.b64encode(val).decode("ascii")
            except OSError:
                continue
    except OSError:
        pass
    return xattrs
