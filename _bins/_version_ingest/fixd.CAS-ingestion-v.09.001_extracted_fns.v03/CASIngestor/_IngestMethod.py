    def _IngestMethod(self, src, dst):
        if dst.exists():
            # Should never reach here
            return
        
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:            
            if self.args.ingest_method == "reflink":
 
 

                self._IngestReflink(src, dst)







            elif self.args.ingest_method == "move":



                self._IngestMove(src, dst)



            elif self.args.ingest_method == "hardlink":
                
                self._IngestHardlink(src, dst)

            elif self.args.ingest_method == "symlink":
                

                self._IngestSoftlink(src, dst)


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
