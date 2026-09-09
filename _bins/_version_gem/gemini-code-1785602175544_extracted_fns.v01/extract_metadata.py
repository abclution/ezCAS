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

def extract_metadata(filepath):
    st = os.stat(filepath)
    return {'path': os.path.abspath(filepath), 'ingested_at': datetime.datetime.now().isoformat(), 'size': st.st_size, 'mtime': st.st_mtime, 'ctime': getattr(st, 'st_ctime', st.st_mtime), 'mode': st.st_mode, 'xattrs': extract_xattrs(filepath)}
