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

def read_sidecar(sidecar_path, fmt='json'):
    if not os.path.exists(sidecar_path):
        return None
    if fmt == 'json':
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        tree = ET.parse(sidecar_path)
        root = tree.getroot()
        data = {'hash': root.findtext('hash', ''), 'algorithm': root.findtext('algorithm', ''), 'instances': {}}
        known_as = root.find('known_as')
        if known_as is not None:
            for inst in known_as.findall('instance'):
                inst_id = inst.get('id')
                inst_data = {}
                for child in inst:
                    if child.tag == 'xattrs':
                        inst_data['xattrs'] = {x.get('name'): x.text for x in child.findall('xattr')}
                    elif child.tag in ('size', 'mode'):
                        inst_data[child.tag] = int(child.text)
                    elif child.tag in ('mtime', 'ctime'):
                        inst_data[child.tag] = float(child.text)
                    else:
                        inst_data[child.tag] = child.text
                data['instances'][inst_id] = inst_data
        return data
