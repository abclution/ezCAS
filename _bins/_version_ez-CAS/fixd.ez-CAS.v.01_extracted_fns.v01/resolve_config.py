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

def resolve_config(args: argparse.Namespace) -> Dict[str, Any]:
    repo = Path(args.repo).resolve()
    repo.mkdir(parents=True, exist_ok=True)
    cfg_path = repo / CONFIG_FILE
    saved = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    conf = vars(args)
    conf['repo'] = repo
    for k, v in saved.items():
        if getattr(args, k) == args_parser.get_default(k):
            conf[k] = v
    keys = ['algo', 'use_external', 'format', 'ingest_method', 'dedupe_action', 'shard_depth']
    cfg_path.write_text(json.dumps({k: conf[k] for k in keys}))
    return conf
