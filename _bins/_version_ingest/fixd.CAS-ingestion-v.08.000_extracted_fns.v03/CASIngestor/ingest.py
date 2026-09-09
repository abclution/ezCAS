    def ingest(self, filepath):
        fpath = Path(filepath).resolve()
        try:
            file_hash = self.hasher.calculate(fpath)
        except Exception as e:
            print(f"ERR (Hash) {fpath}: {e}")
            return

        cas_path = self._get_storage_path(file_hash)
        sidecar_path = cas_path.parent / (cas_path.name + self.args.suffix)
        is_duplicate = cas_path.exists()

        path_id, meta = self._get_metadata(fpath)

        if not is_duplicate:
            try:
                self._ingest_method(fpath, cas_path)
            except Exception as e:
                print(f"ERR (Copy) {fpath}: {e}")
                return

        if sidecar_path.exists():
            data = self.sidecar_handler.load(sidecar_path)
        else:
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            data = self.sidecar_handler.create_empty(file_hash, self.args.algo)

        data["known_as"][path_id] = meta
        self.sidecar_handler.save(sidecar_path, data)

        if is_duplicate:
            print(f"DUPLICATE -> {file_hash[:8]}... ({fpath})")
            self._log_dedup_action(fpath, cas_path)
            
            #if self.args.force:
            #    self._do_dedup_action(fpath, cas_path)
            
            # This is called when it already is determined to be a duplicate
#            if self.args.force and not self.args.link_mode == "move" :
            #if self.args.force :
            #    print(f"Action forced, performing immediate {self.args.dedup_mode} ")
            #    self._do_dedup_action(fpath, cas_path)

            # # This is called when it already is determined to be a duplicate
            # if self.args.force and self.args.link_mode == "move" :

            #     if self.args.dedup_mode == "ignore" and not self.args.force :
            #         raise SystemExit("Move + ignore would isolate the files in the CAS, please choose another method.\n Or add -f/--force if you are sure.")

            #     if self.args.dedup_mode == "delete" and not self.args.force :
            #         raise SystemExit("Move + delete would isolate the files in the CAS, please choose another method.\n Or add -f/--force if you are sure.")

            #     print(f"Action forced, performing immediate {self.args.dedup_mode} ")
            #     self._do_dedup_action(fpath, cas_path)





        else:
            print(f"OK -> {file_hash[:8]}... ({fpath})")
