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

def calculate_hash(filepath, algo='sha256'):
    h = hashlib.new(algo)
    with open(filepath, 'rb') as f:
        while (chunk := f.read(65536)):
            h.update(chunk)
    return h.hexdigest()
