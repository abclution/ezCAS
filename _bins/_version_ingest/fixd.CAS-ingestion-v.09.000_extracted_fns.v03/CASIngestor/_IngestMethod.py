    def _IngestMethod(self, src, dst):
        if dst.exists():
            # Should never reach here
            return
        
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:            
            if self.args.ingest_method == "reflink":
                subprocess.run(
                    ["cp", "--preserve=all", "--reflink=always", src, dst],
                    check=True,
                    capture_output=True,
                )

            elif self.args.ingest_method == "move":

                if self.args.dedupe_action == "ignore" and not self.args.force:
                    raise SystemExit(
                        "Move + ignore would isolate the files in the CAS, please choose another method.\n Or add -f/--force if you are sure."
                    )

                if self.args.dedupe_action == "delete" and not self.args.force:
                    raise SystemExit(
                        "Move + delete would isolate the files in the CAS, please choose another method.\n Or add -f/--force if you are sure."
                    )

                subprocess.run(
                    ["mv", "-vn", src, dst],
                    check=True,
                    capture_output=True,
                )
                # When moving, unless forcing a delete/ignore, we want to leave something to resolve to the CAS entry. Doing dedupe action on every file (hard/sym/reflink)  accomplishes it.
                self._DoDedupeAction(src, dst)
                #    def _DoDedupeAction(self, ORIGINRecord, inCASRecord):

            elif self.args.ingest_method == "hardlink":
                os.link(src, dst)
            elif self.args.ingest_method == "symlink":
                os.symlink(src, dst)
            else:
                raise SystemExit(
                    "No availiable methods to ingest. Read only filesystem?"
                )

        except (OSError, subprocess.CalledProcessError) as e:
            if self.args.ingest_method == "reflink":
                raise SystemExit(f"Reflink failed: {e}")
            elif self.args.ingest_method == "move":
                raise SystemExit(f"Move failed: {e}")
            elif self.args.ingest_method == "hardlink":
                raise SystemExit(f"Hardlink failed: {e}")
            elif self.args.ingest_method == "symlink":
                raise SystemExit(f"Symlink failed: {e}")
            else:
                raise SystemExit(f"Unknown failure: {e}")
