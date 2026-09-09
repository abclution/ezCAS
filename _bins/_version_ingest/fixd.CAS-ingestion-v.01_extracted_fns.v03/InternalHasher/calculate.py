    def calculate(self, filepath):
        h = hashlib.new(self.alg_name)
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
