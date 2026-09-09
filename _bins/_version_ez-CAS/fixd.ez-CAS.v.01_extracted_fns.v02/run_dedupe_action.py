def run_dedupe_action(src: Path, dst: Path, action: str):
    q_src, q_dst = shlex.quote(str(src)), shlex.quote(str(dst))
    if action == "ignore":
        return
    if action == "hardlink":
        subprocess.run(
            ["ln", "-vf", str(dst), str(src)], check=True, capture_output=True
        )
    elif action == "symlink":
        subprocess.run(
            ["ln", "-vsf", str(dst), str(src)], check=True, capture_output=True
        )
    elif action == "reflink":
        # Edge case with hardlinked files need to remove before reflinking them
        #  as they are same file.
        os.remove(src)
        subprocess.run(
            [
                "cp",
                "-v",
                "-f",
                "--preserve=all",
                "--reflink=always",
                str(dst),
                str(src),
            ],
            check=True,
            capture_output=True,
        )
    elif action == "delete":
        os.remove(q_src)
        subprocess.run(
            [
                "rm",
                "-v",
                "-f",
                {q_src},
            ],
            check=True,
            capture_output=True,
        )
