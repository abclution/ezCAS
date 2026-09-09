    def _do_dedup_action(self, ORIGINRecord, inCASRecord):
              
        if self.args.dedup_mode == "ignore":
            return

        ORIGINRecord_fmt = shlex.quote(str(ORIGINRecord))
        inCASRecord_fmt = shlex.quote(str(inCASRecord))

        if self.args.dedup_mode == "hardlink" :
            subprocess.run(
                ["ln", "-vf", inCASRecord, ORIGINRecord],
                check=True,
                capture_output=True,
            )
            print(f"HARDLINKING -> \n{inCASRecord_fmt}\n{inCASRecord}\n to \n{ORIGINRecord_fmt}\n{ORIGINRecord}")

        elif self.args.dedup_mode == "symlink" :
            subprocess.run(
                ["ln", "-vsf", inCASRecord, ORIGINRecord],
                check=True,
                capture_output=True,
            )
            print(f"SYMLINKING ->  \n{inCASRecord_fmt}\n{inCASRecord}\n to \n{ORIGINRecord_fmt}\n{ORIGINRecord}")

        elif self.args.dedup_mode == "reflink" :
            subprocess.run(
                [
                    "cp",
                    "-v",
                    "--preserve=all",
                    "--reflink=always",
                    inCASRecord,
                    ORIGINRecord,
                ],
                check=True,
                capture_output=True,
            )
            print(f"COPYING (REFLINK) -> \n{inCASRecord_fmt}\n{inCASRecord}\n to \n{ORIGINRecord_fmt}\n{ORIGINRecord}")

        elif self.args.dedup_mode == "delete" :
            subprocess.run(
                ["rm", "-fv", "ORIGINRecord"],
                check=True,
                capture_output=True,
            )
            print(f"DELETING -> \n{ORIGINRecord_fmt}\n{ORIGINRecord}")
