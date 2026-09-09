    def migrate_structure(self):
        print(f"Starting migration to shard depth: {self.args.shard_depth}")
        if self.args.shard_depth == 0:
            print("Depth 0: Moving files to root...")

        for item in self.repo.rglob("*"):
            if (
                not item.is_file()
                or item.name == CONFIG_FILE
                or item.name == DEDUP_SCRIPT
            ):
                continue

            if item.name.endswith(self.args.suffix):
                file_hash = item.name[: -len(self.args.suffix)]
            else:
                file_hash = item.name

            correct_path = self._GetStoragePath(file_hash)
            if item.name.endswith(self.args.suffix):
                correct_path = correct_path.parent / (
                    correct_path.name + self.args.suffix
                )

            if item.resolve() != correct_path.resolve():
                correct_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"Moving {item.name[:8]}... -> {correct_path.parent.name}/")
                shutil.move(item, correct_path)

        for root, dirs, files in os.walk(self.repo, topdown=False):
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass
        print("Migration complete.")
