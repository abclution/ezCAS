    def save(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
