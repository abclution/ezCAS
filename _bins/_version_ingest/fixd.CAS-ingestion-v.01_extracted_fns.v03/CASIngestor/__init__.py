    def __init__(self, args):
        self.repo = Path(args.repo).resolve()
        self.repo.mkdir(parents=True, exist_ok=True)
        self.args = self._resolve_config(args)
        self.hasher = self._get_hasher()
        self.sidecar_handler = (XMLHandler() if self.args.format == 'xml' 
                                else JSONHandler())
