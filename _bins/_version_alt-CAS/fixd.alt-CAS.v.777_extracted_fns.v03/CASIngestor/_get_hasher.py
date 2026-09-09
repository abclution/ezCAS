    def _get_hasher(self):
        algo = self.args.algo
        if self.args.use_external:
            return ExternalHasher(algo)
        return InternalHasher(algo)
