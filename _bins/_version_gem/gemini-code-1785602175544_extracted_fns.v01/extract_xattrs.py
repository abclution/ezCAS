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

def extract_xattrs(filepath):
    xattrs = {}
    if not hasattr(os, 'listxattr'):
        return xattrs
    try:
        attrs = os.listxattr(filepath)
        for attr in attrs:
            try:
                val = os.getxattr(filepath, attr)
                xattrs[attr] = base64.b64encode(val).decode('ascii')
            except OSError:
                continue
    except OSError:
        pass
    return xattrs
