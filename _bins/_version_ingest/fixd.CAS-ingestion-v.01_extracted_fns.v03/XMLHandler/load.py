    def load(self, path):
        tree = ET.parse(path)
        root = tree.getroot()
        data = {
            "hash": root.find("hash").text,
            "algorithm": root.find("algorithm").text,
            "known_as": {}
        }
        for inst in root.find("known_as"):
            meta = {child.tag: child.text for child in inst}
            data["known_as"][inst.get("id")] = meta
        return data
