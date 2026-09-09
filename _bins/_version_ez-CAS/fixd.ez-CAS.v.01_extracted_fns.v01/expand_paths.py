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

def expand_paths(paths: list, recursive: bool) -> Generator[Path, None, None]:
    for p_str in paths:
        p = Path(p_str)
        if p.is_symlink():
            continue
        res = p.resolve()
        if res.is_file():
            yield res
        elif res.is_dir() and recursive:
            for sub in res.rglob('*'):
                if not sub.is_symlink() and sub.is_file():
                    yield sub
