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

def get_metadata(filepath: Path) -> tuple[str, Dict[str, Any]]:
    stat = filepath.stat()
    path_id = hashlib.sha256(str(filepath).encode()).hexdigest()
    meta = {'path': str(filepath), 'ingested_at': datetime.now().isoformat(), 'size': stat.st_size, 'mtime': stat.st_mtime, 'mode': oct(stat.st_mode)[-3:], 'xattrs': get_file_xattrs(filepath)}
    return (path_id, meta)
