import os
import sys
import hashlib
import json
import argparse
import subprocess
import shutil
import shlex
import base64
import time
from icecream import ic
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Generator
CONFIG_FILE = '.CAS-config'
DEFAULT_SIDECAR_SUFFIX = '.known-as'
DEDUP_SCRIPT = f'CAS-dedupActionlist_{epoch_time}.sh'

def load_sidecar(path: Path, fmt: str) -> Dict[str, Any]:
    if fmt == 'json':
        with open(path, 'r') as f:
            return json.load(f)
    tree = ET.parse(path)
    root = tree.getroot()
    data = {'hash': root.find('hash').text, 'algorithm': root.find('algorithm').text, 'known_as': {}}
    for inst in root.find('known_as'):
        meta = {}
        for child in inst:
            if child.tag == 'xattrs':
                meta['xattrs'] = {x.attrib['key']: x.text for x in child}
            else:
                meta[child.tag] = child.text
        data['known_as'][inst.get('id')] = meta
    return data
