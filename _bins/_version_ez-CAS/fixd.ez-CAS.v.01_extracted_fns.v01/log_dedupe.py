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

def log_dedupe(src: Path, dst: Path, action: str, force: bool, f_hash):
    q_src, q_dst = (shlex.quote(str(src)), shlex.quote(str(dst)))
    cmds = {'hardlink': f'ln -vf {q_dst} {q_src}\n', 'symlink': f'ln -vsf {q_dst} {q_src}\n', 'reflink': f'rm -vf {q_src} && cp -v -f --preserve=all --reflink=always {q_dst} {q_src}\n', 'delete': f'rm -fv {q_src}\n', 'ignore': f'mv -vn {q_src} {q_src}.DUPE-IN-CAS \n'}
    if action == 'ignore':
        entry = f"# DUPLICATE FILE SET\n# - '{src}'\n# - '{q_dst}'\n{cmds.get(action, '')}\n\n"
        with open(DEDUP_SCRIPT, 'a') as f:
            f.write(entry)
        return
    if force:
        entry += f'# Command line switch force enabled: {action} performed.\n'
        run_dedupe_action(src, dst, action)
    with open(DEDUP_SCRIPT, 'a') as f:
        f.write(entry)
