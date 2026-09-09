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

def atomic_write(target_path, content, is_bytes=False):
    dirname = os.path.dirname(target_path)
    mode = 'wb' if is_bytes else 'w'
    with tempfile.NamedTemporaryFile(mode, dir=dirname, delete=False) as tf:
        tf.write(content)
        temp_name = tf.name
    os.replace(temp_name, target_path)
