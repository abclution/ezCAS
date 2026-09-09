def log_dedupe(src: Path, dst: Path, action: str, force: bool, f_hash):
    q_src, q_dst = shlex.quote(str(src)), shlex.quote(str(dst))
    cmds = {
        "hardlink": f"ln -vf {q_dst} {q_src}\n",
        "symlink": f"ln -vsf {q_dst} {q_src}\n",
        "reflink": f"rm -vf {q_src} && cp -v -f --preserve=all --reflink=always {q_dst} {q_src}\n",
        "delete": f"rm -fv {q_src}\n",
        "ignore": f"mv -vn {q_src} {q_src}.DUPE-IN-CAS \n",
        # "ignore": "Ignore option set, no action performed.\n",

    }

    if action == "ignore":
        # entry = f"# Duplicate: {src}\n{cmds.get(action, '')}"
        # entry = f"# DUPLICATE: {src} EXISTS AS {f_hash} \n{cmds.get(action, '')}"
        #entry = f"# DUPLICATE FILE SET\n    \'{src}\'\n    \'{q_dst}\'\n{cmds.get(action, '')}\n\n"
        entry = f"# DUPLICATE FILE SET\n# - \'{src}'\n# - \'{q_dst}\'\n{cmds.get(action, '')}\n\n"

        with open(DEDUP_SCRIPT, "a") as f:
            f.write(entry)
        return
    # entry = f"# Duplicate: {src}\n{cmds.get(action, '')}"

    if force:
        entry += f"# Command line switch force enabled: {action} performed.\n"
        run_dedupe_action(src, dst, action)
    with open(DEDUP_SCRIPT, "a") as f:
        f.write(entry)
