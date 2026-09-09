import os
import sys
import hashlib
import json
import argparse
import subprocess
import shutil
import platform
import shlex
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict
CONFIG_FILE = '.CAS-config'
DEFAULT_SIDECAR_SUFFIX = '.known-as'
DEDUP_SCRIPT = 'CAS-dedupActionlist.sh'

def get_raw_xattrs(filepath: Path) -> Dict[str, str]:
    """Retrieves raw xattrs and returns them as Base64 encoded strings."""
    attrs = {}
    try:
        names = os.listxattr(filepath, follow_symlinks=False)
        for name in names:
            try:
                val = os.getxattr(filepath, name, follow_symlinks=False)
                attrs[name] = base64.b64encode(val).decode('utf-8')
            except OSError:
                continue
    except (AttributeError, OSError):
        pass
    return attrs
