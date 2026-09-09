def handle_dedup(src, blob_path, args, repo_root):
    mode = args.dedup_mode
    quoted_src = shlex.quote(src)
    quoted_blob = shlex.quote(blob_path)
    cmds = []

    if mode == "ignore":
        log_and_script(
            "dedup", [], f"Duplicate found for {src}. Action: Ignore", repo_root
        )
    elif mode == "delete":
        cmds.append(f"rm -f {quoted_src}")
        log_and_script(
            "dedup",
            cmds,
            f"Duplicate found for {src}. Action: Delete",
            repo_root,
        )
        os.remove(src)
    elif mode == "hardlink":
        cmds.append(f"ln -f {quoted_blob} {quoted_src}")
        log_and_script(
            "dedup",
            cmds,
            f"Duplicate found for {src}. Action: Hardlink",
            repo_root,
        )
        os.remove(src)
        os.link(blob_path, src)
    elif mode == "softlink":
        cmds.append(f"ln -sf {quoted_blob} {quoted_src}")
        log_and_script(
            "dedup",
            cmds,
            f"Duplicate found for {src}. Action: Softlink",
            repo_root,
        )
        os.remove(src)
        os.symlink(blob_path, src)
