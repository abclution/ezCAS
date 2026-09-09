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

def get_timestamp_prefix():
    now = datetime.datetime.now()
    return f"{int(time.time())}_{now.strftime('%Y.%m.%d')}"
