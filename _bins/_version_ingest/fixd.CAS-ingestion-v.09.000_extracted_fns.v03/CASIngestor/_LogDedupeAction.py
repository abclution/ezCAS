    def _LogDedupeAction(self, src, dst):
        if self.args.dedupe_action == "ignore":
            return
        q_src = shlex.quote(str(src))
        q_dst = shlex.quote(str(dst))
        action_cmd = f"# Duplicate: {src}\n"
        if self.args.dedupe_action == "hardlink":
            action_cmd += f"ln -vf {q_dst} {q_src}\n"
        elif self.args.dedupe_action == "symlink":
            action_cmd += f"ln -vsf {q_dst} {q_src}\n"
        elif self.args.dedupe_action == "reflink":
            action_cmd += f"cp -v --preserve=all --reflink=always {q_src} {q_dst}\n"
        elif self.args.dedupe_action == "delete":
            action_cmd += f"rm -fv {q_src}\n"
        if self.args.force:
            print(f"Action forced, performing immediate {self.args.dedupe_action}")
            action_cmd += (
                f"# Force switch enabled, {self.args.dedupe_action} command processed.\n"
            )
            self._DoDedupeAction(src, dst)
        with open(DEDUP_SCRIPT, "a") as f:
            f.write(action_cmd)
