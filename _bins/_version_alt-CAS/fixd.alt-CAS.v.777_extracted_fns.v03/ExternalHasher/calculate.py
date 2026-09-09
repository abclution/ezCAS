    def calculate(self, filepath):
        res = subprocess.check_output([self.cmd, filepath]).decode().strip()
        return res.split()[0]
