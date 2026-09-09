    def save(self, path, data):
        root = ET.Element("entry")
        ET.SubElement(root, "hash").text = data["hash"]
        ET.SubElement(root, "algorithm").text = data["algorithm"]
        ka = ET.SubElement(root, "known_as")

        for pid, meta in data["known_as"].items():
            inst = ET.SubElement(ka, "instance", id=pid)
            for k, v in meta.items():
                if k == "xattrs":
                    x_node = ET.SubElement(inst, "xattrs")
                    for x_key, x_val in v.items():
                        sub = ET.SubElement(x_node, "attr", key=x_key)
                        sub.text = str(x_val)
                else:
                    ET.SubElement(inst, k).text = str(v)

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(path, encoding="utf-8", xml_declaration=True)
