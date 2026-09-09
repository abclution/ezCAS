    def _IngestMove(self, src, dst):

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
