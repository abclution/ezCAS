    def _log_dedup_action(self, src, dst):
        if self.args.dedup_mode == "ignore":
            return
        q_src = shlex.quote(str(src))
        q_dst = shlex.quote(str(dst))
        action_cmd = f"# Duplicate: {src}\n"
        if self.args.dedup_mode == "hardlink":
            action_cmd += f"ln -vf {q_dst} {q_src}\n"
        elif self.args.dedup_mode == "symlink":
            action_cmd += f"ln -vsf {q_dst} {q_src}\n"
        elif self.args.dedup_mode == "reflink":
            action_cmd += f"cp -v --preserve=all --reflink=always {q_src} {q_dst}\n"
        elif self.args.dedup_mode == "delete":
            action_cmd += f"rm -fv {q_src}\n"
        if self.args.force :
            print(f"Action forced, performing immediate {self.args.dedup_mode}")
            action_cmd += f"# Force switch enabled, {self.args.dedup_mode} command processed.\n"
            self._do_dedup_action(src, dst)
        with open(DEDUP_SCRIPT, "a") as f:
            f.write(action_cmd)
