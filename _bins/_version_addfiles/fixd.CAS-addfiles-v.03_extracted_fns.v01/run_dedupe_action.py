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

def run_dedupe_action(src: Path, dst: Path, action: str):
    if action == 'ignore':
        return
    if action == 'hardlink':
        subprocess.run(['ln', '-vf', str(dst), str(src)], check=True, capture_output=True)
    elif action == 'symlink':
        subprocess.run(['ln', '-vsf', str(dst), str(src)], check=True, capture_output=True)
    elif action == 'reflink':
        os.remove(src)
        subprocess.run(['cp', '-v', '-f', '--preserve=all', '--reflink=always', str(dst), str(src)], check=True, capture_output=True)
    elif action == 'delete':
        subprocess.run(['rm', '-v', '-f', str(src)], check=True, capture_output=True)
