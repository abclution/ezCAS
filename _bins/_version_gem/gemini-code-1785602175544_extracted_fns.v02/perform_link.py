def perform_link(src, dst, mode):
    if mode == "reflink":
        try:
            res = subprocess.run(
                ["cp", "--reflink=always", src, dst],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            shutil.copy2(src, dst)
            return True
    elif mode == "copy":
        shutil.copy2(src, dst)
        return True
    elif mode == "move":
        shutil.move(src, dst)
        return True
    elif mode == "hardlink":
        os.link(src, dst)
        return True
    elif mode == "symlink":
        os.symlink(os.path.abspath(src), dst)
        return True
    return False
