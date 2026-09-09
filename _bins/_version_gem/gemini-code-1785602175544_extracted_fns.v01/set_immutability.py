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

def set_immutability(filepath, enable=True):
    flag = '+i' if enable else '-i'
    if sys.platform.startswith('linux'):
        try:
            subprocess.run(['chattr', flag, filepath], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass
