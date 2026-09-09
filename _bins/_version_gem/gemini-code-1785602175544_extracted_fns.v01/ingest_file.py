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

def ingest_file(src, repo_root, cfg, args):
    if not os.path.isfile(src) or os.path.islink(src):
        return
    file_hash = calculate_hash(src, cfg['algo'])
    shard_dir = get_shard_dir(repo_root, file_hash, cfg['shard_depth'])
    os.makedirs(shard_dir, exist_ok=True)
    blob_path = os.path.join(shard_dir, file_hash)
    sidecar_path = f"{blob_path}{cfg['suffix']}"
    meta = extract_metadata(src)
    inst_id = hashlib.new(cfg['algo'], f"{meta['path']}_{meta['mtime']}_{meta['size']}".encode('utf-8')).hexdigest()
    sidecar_data = read_sidecar(sidecar_path, cfg['format']) or {'hash': file_hash, 'algorithm': cfg['algo'], 'instances': {}}
    sidecar_data['instances'][inst_id] = meta
    if not os.path.exists(blob_path):
        perform_link(src, blob_path, args.link_mode)
        if args.link_mode != 'symlink':
            set_immutability(blob_path, True)
        write_sidecar(sidecar_path, sidecar_data, cfg['format'])
        log_and_script('ingest', [], f'Ingested new blob: {file_hash} from {src}', repo_root)
    else:
        existing_mtime = os.stat(blob_path).st_mtime
        if meta['mtime'] < existing_mtime:
            set_immutability(blob_path, False)
            perform_link(src, blob_path, 'copy')
            set_immutability(blob_path, True)
            log_and_script('origin_update', [], f'Updated origin for {file_hash} with older file: {src}', repo_root)
        write_sidecar(sidecar_path, sidecar_data, cfg['format'])
        handle_dedup(src, blob_path, args, repo_root)
