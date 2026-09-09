    def load(self, path):
        tree = ET.parse(path)
        root = tree.getroot()
        data = {
            "hash": root.find("hash").text,
            "algorithm": root.find("algorithm").text,
            "known_as": {}
        }
        for inst in root.find("known_as"):
            meta = {}
            for child in inst:
                if child.tag == "xattrs":
                    x_dict = {}
                    for x in child:
                        x_dict[x.attrib['key']] = x.text
                    meta["xattrs"] = x_dict
                else:
                    meta[child.tag] = child.text
            data["known_as"][inst.get("id")] = meta
        return data
