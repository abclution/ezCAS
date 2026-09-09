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

def calculate_hash(filepath: Path, algo: str, use_external: bool) -> str:
    if use_external:
        cmd = f'{algo}sum'
        res = subprocess.check_output([cmd, str(filepath)]).decode().strip()
        return res.split()[0]
    h = hashlib.new(algo)
    with open(filepath, 'rb') as f:
        while (chunk := f.read(8192)):
            h.update(chunk)
    return h.hexdigest()
