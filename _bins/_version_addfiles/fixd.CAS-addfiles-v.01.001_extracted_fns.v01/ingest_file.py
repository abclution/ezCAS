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

def ingest_file(src: Path, conf: Dict[str, Any]):
    try:
        f_hash = calculate_hash(src, conf['algo'], conf['use_external'])
        cas_path = get_storage_path(conf['repo'], f_hash, conf['shard_depth'])
        sidecar_path = cas_path.parent / (cas_path.name + conf['suffix'])
        is_dup = cas_path.exists()
        p_id, meta = get_metadata(src)
        if not is_dup:
            cas_path.parent.mkdir(parents=True, exist_ok=True)
            meth = conf['ingest_method']
            if meth == 'reflink':
                subprocess.run(['cp', '--preserve=all', '--reflink=always', str(src), str(cas_path)], check=True)
            elif meth == 'move':
                if conf['dedupe_action'] in ['ignore', 'delete'] and (not conf['force']):
                    print(f"ERR: Move + {conf['dedupe_action']} requires --force")
                    return
                subprocess.run(['mv', '-vn', str(src), str(cas_path)], check=True)
                run_dedupe_action(src, cas_path, conf['dedupe_action'])
            elif meth == 'hardlink':
                os.link(src, cas_path)
            elif meth == 'symlink':
                os.symlink(src, cas_path)
        data = load_sidecar(sidecar_path, conf['format']) if sidecar_path.exists() else {'hash': f_hash, 'algorithm': conf['algo'], 'known_as': {}}
        data['known_as'][p_id] = meta
        save_sidecar(sidecar_path, data, conf['format'])
        if is_dup:
            print(f'DUPLICATE -> {f_hash[:8]}... ({src})')
            log_dedupe(src, cas_path, conf['dedupe_action'], conf['force'])
        else:
            print(f'OK -> {f_hash[:8]}... ({src})')
    except Exception as e:
        print(f'ERR {src}: {e}')
