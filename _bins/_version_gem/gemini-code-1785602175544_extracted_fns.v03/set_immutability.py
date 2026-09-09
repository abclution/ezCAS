def set_immutability(filepath, enable=True):
    flag = "+i" if enable else "-i"
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(
                ["chattr", flag, filepath],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass
