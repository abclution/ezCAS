    def _log_dedup_action(self, src, dst):
        if self.args.dedup_mode == "ignore":
            return
        q_src = shlex.quote(str(src))
        q_dst = shlex.quote(str(dst))
        action_cmd = f"# Duplicate: {src}\n"
        if self.args.dedup_mode == "hardlink":
            action_cmd += f"ln -f {q_dst} {q_src}\n"
        elif self.args.dedup_mode == "softlink":
            action_cmd += f"ln -sf {q_dst} {q_src}\n"
        elif self.args.dedup_mode == "delete":
            action_cmd += f"rm {q_src}\n"
        with open(DEDUP_SCRIPT, "a") as f:
            f.write(action_cmd)
