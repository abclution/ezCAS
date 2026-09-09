    def _do_dedup_action(self, ORIGINRecord, inCASRecord):

        ORIGINRecord_fmt = shlex.quote(str(ORIGINRecord))
        inCASRecord_fmt = shlex.quote(str(inCASRecord))

        if self.args.dedupe_action == "ignore":
            return


        if self.args.dedupe_action == "hardlink":
            subprocess.run(
                ["ln", "-vf", inCASRecord, ORIGINRecord],
                check=True,
                capture_output=True,
            )
            print(
                f"HARDLINKING -> \n{inCASRecord}\n to \n{ORIGINRecord}"
            )

        elif self.args.dedupe_action == "symlink":
            subprocess.run(
                ["ln", "-vsf", inCASRecord, ORIGINRecord],
                check=True,
                capture_output=True,
            )
            print(
                f"SYMLINKING ->  \n{inCASRecord}\n to \n{ORIGINRecord}"
            )

        elif self.args.dedupe_action == "reflink":
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
            print(
                f"COPYING (REFLINK) -> \n{inCASRecord}\n to \n{ORIGINRecord}"
            )

        elif self.args.dedupe_action == "delete":
            os.remove(ORIGINRecord)
            print(f"DELETING -> \n{ORIGINRecord}")
