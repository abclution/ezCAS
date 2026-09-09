import os
import sys
import hashlib
import json
import argparse
import subprocess
import shutil
import shlex
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Generator
CONFIG_FILE = '.CAS-config'
DEFAULT_SIDECAR_SUFFIX = '.known-as'
DEDUP_SCRIPT = 'CAS-dedupActionlist.sh'

def log_dedupe(src: Path, dst: Path, action: str, force: bool):
    if action == 'ignore':
        return
    q_src, q_dst = (shlex.quote(str(src)), shlex.quote(str(dst)))
    cmds = {'hardlink': f'ln -vf {q_dst} {q_src}\n', 'symlink': f'ln -vsf {q_dst} {q_src}\n', 'reflink': f'cp -v --preserve=all --reflink=always {q_dst} {q_src}\n', 'delete': f'rm -fv {q_src}\n'}
    entry = f"# Duplicate: {src}\n{cmds.get(action, '')}"
    if force:
        entry += f'# Force enabled: {action} performed.\n'
        run_dedupe_action(src, dst, action)
    with open(DEDUP_SCRIPT, 'a') as f:
        f.write(entry)
