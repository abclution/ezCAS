    def _reflink_copy(self, src, dst):
        if dst.exists(): return
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if platform.system() == 'Darwin':
                os.clonefile(src, dst)
            else:
                subprocess.run(['cp', '--reflink=always', src, dst], 
                             check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError) as e:
            if self.args.link_mode == 'reflink': raise Exception(f"Reflink failed: {e}")
            elif self.args.link_mode == 'hardlink': os.link(src, dst)
            elif self.args.link_mode == 'symlink': os.symlink(src, dst)
            else: shutil.copy2(src, dst)
