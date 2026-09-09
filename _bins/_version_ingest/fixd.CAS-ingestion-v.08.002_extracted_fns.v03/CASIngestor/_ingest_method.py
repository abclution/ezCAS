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
                        ["cp", "--preserve=all", "--reflink=always", src, dst],
                        check=True,
                        capture_output=True,
                    )
                elif self.args.link_mode == "move":
                    subprocess.run(
                        ["mv", "-n", src, dst],
                        check=True,
                        capture_output=True,
                    )
                    
                    if self.args.dedup_mode == "ignore" and not self.args.force :
                        raise SystemExit("Move + ignore would isolate the files in the CAS, please choose another method.\n Or add -f/--force if you are sure.")

                    if self.args.dedup_mode == "delete" and not self.args.force :
                        raise SystemExit("Move + delete would isolate the files in the CAS, please choose another method.\n Or add -f/--force if you are sure.")
                
                    # print(f"Move chosen as ingest method, using {self.args.dedup_mode} method for preserving of incoming files. ")

                    # subprocess.run(
                    #         ["sleep", "5" ],
                    #         check=True,
                    #         capture_output=True,
                    #     )

                    # Running dedup in this stanza actually performs the action on every incoming file.
                    # As the check for it being a duplicate is bypassed, this is wanted in some cases.
                    self._do_dedup_action(src, dst)




                    # subprocess.run(
                    #     ["cp", "--preserve=all", "--reflink=always", dst, src],
                    #     check=True,
                    #     capture_output=True,
                    # )

                elif self.args.link_mode == "hardlink":
                    os.link(src, dst)
                elif self.args.link_mode == "symlink":
                    os.symlink(src, dst)
                else:
                    raise SystemExit("No availiable methods to ingest. Read only filesystem?")
                    

                # if self.args.force :
                #     print(f"Action forced, performing immediate {self.args.dedup} ")
                #     self._do_dedup_action(src, dst)




        except (OSError, subprocess.CalledProcessError) as e:
            if self.args.link_mode == "reflink":
                raise SystemExit(f"Reflink failed: {e}")
            elif self.args.link_mode == "move":
                raise SystemExit(f"Move failed: {e}")
            elif self.args.link_mode == "hardlink":
                raise SystemExit(f"Hardlink failed: {e}")
            elif self.args.link_mode == "symlink":
                raise SystemExit(f"Symlink failed: {e}")
            else:
                raise SystemExit(f"Unknown failure: {e}")
