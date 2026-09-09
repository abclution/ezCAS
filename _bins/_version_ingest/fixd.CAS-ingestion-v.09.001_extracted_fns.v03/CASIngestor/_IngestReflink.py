    def _IngestReflink(self, src, dst):

        subprocess.run(
            ["cp", "--preserve=all", "--reflink=always", src, dst],
            check=True,
            capture_output=True,
        )
