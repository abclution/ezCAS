def extract_metadata(filepath):
    st = os.stat(filepath)
    return {
        "path": os.path.abspath(filepath),
        "ingested_at": datetime.datetime.now().isoformat(),
        "size": st.st_size,
        "mtime": st.st_mtime,
        "ctime": getattr(st, "st_ctime", st.st_mtime),
        "mode": st.st_mode,
        "xattrs": extract_xattrs(filepath),
    }
