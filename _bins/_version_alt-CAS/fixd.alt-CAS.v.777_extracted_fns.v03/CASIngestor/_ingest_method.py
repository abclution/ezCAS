    def _ingest_method(self, src, dst):
        if dst.exists():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if platform.system() == "Darwin":
                os.clonefile(src, dst)
            else:
                if self.args.link_mode == "reflink":
                    subprocess.run(
                        ["cp", "--preserve=all --reflink=always", src, dst],
                        check=True,
                        capture_output=True,
                    )

                elif self.args.link_mode == "hardlink":
                    os.link(src, dst)
                elif self.args.link_mode == "symlink":
                    os.symlink(src, dst)
                else:
                    shutil.copy2(src, dst)

        except (OSError, subprocess.CalledProcessError) as e:
            if self.args.link_mode == "reflink":
                raise Exception(f"Reflink failed: {e}")
            elif self.args.link_mode == "hardlink":
                raise Exception(f"Hardlink failed: {e}")
            elif self.args.link_mode == "symlink":
                raise Exception(f"Symlink failed: {e}")
            else:
                raise Exception(f"Regular copy failed: {e}")
