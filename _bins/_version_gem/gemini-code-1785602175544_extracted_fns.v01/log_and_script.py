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

def log_and_script(action_type, commands, log_message, repo_root):
    ts = get_timestamp_prefix()
    log_file = os.path.join(repo_root, f'{ts}--LOG_{action_type}.log')
    script_file = os.path.join(repo_root, f'{ts}--SCRIPT_{action_type}.sh')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f'[{datetime.datetime.now().isoformat()}] {log_message}\n')
    if commands:
        with open(script_file, 'a', encoding='utf-8') as f:
            f.write('#!/usr/bin/env bash\nset -euo pipefail\n')
            for cmd in commands:
                f.write(f'{cmd}\n')
        os.chmod(script_file, 493)
