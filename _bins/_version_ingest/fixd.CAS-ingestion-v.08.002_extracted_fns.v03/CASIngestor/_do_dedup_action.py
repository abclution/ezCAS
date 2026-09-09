    def _do_dedup_action(self, ORIGINRecord, inCASRecord):


        ORIGINRecord_fmt = shlex.quote(str(ORIGINRecord))
        inCASRecord_fmt = shlex.quote(str(inCASRecord))


        if self.args.dedup_mode == "ignore":
            return

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
            os.remove(ORIGINRecord)
            print(f"DELETING -> \n{ORIGINRecord_fmt}\n{ORIGINRecord}")
