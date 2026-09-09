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

def get_storage_path(repo: Path, file_hash: str, depth: int) -> Path:
    if depth == 0:
        return repo / file_hash
    parts = [file_hash[i * 2:i * 2 + 2] for i in range(depth)]
    return repo.joinpath(*parts) / file_hash
