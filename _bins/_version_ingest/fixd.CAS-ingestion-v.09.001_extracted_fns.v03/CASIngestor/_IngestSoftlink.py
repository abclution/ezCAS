    def _IngestSoftlink(self, src, dst):

        os.symlink(src, dst)
