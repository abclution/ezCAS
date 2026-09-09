import os
import sys
import hashlib
import json
import argparse
import subprocess
import shutil
import platform
import shlex
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
CONFIG_FILE = '.CAS-config'
DEFAULT_SIDECAR_SUFFIX = '.known-as'
DEDUP_SCRIPT = 'fixd_dedup_actions.sh'

def _expand_paths(paths, recursive):
    for p_str in paths:
        p = Path(p_str).resolve()
        if p.is_file():
            yield p
        elif p.is_dir() and recursive:
            for sub in p.rglob('*'):
                if sub.is_file():
                    yield sub
