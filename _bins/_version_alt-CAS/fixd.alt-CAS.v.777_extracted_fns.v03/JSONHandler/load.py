    def load(self, path):
        with open(path, "r") as f:
            return json.load(f)
