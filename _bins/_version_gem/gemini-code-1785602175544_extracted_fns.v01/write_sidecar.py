import argparse
import base64
import datetime
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
CONFIG_FILE = '.CAS_datastore.config'

def write_sidecar(sidecar_path, data, fmt='json'):
    if fmt == 'json':
        content = json.dumps(data, indent=2)
        atomic_write(sidecar_path, content, is_bytes=False)
    else:
        root = ET.Element('entry')
        ET.SubElement(root, 'hash').text = data.get('hash', '')
        ET.SubElement(root, 'algorithm').text = data.get('algorithm', '')
        known_as = ET.SubElement(root, 'known_as')
        for inst_id, inst in data.get('instances', {}).items():
            inst_el = ET.SubElement(known_as, 'instance', id=inst_id)
            for k, v in inst.items():
                if k == 'xattrs':
                    x_el = ET.SubElement(inst_el, 'xattrs')
                    for xk, xv in v.items():
                        ET.SubElement(x_el, 'xattr', name=xk).text = xv
                else:
                    ET.SubElement(inst_el, k).text = str(v)
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        dirname = os.path.dirname(sidecar_path)
        with tempfile.NamedTemporaryFile('wb', dir=dirname, delete=False) as tf:
            tree.write(tf, encoding='utf-8', xml_declaration=True)
            temp_name = tf.name
        os.replace(temp_name, sidecar_path)
