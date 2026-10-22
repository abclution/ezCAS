#!/usr/bin/env python3
import argparse
import base64
import datetime
from datetime import date
import hashlib
import json
import os
import errno
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as XmlTree
from pathlib import Path
from tzlocal import get_localzone

from icecream import ic

CONFIG_FILE = ".CAS_datastore.config"

# CHANGELOG
# +SKIP ZERO BYTE FILES
# +INSTANCE TS ONE TIME FOR LOGGING
# +RENAME ET import to XmlTree


##################################################################
nowStart = datetime.datetime.now()


def get_TS_ISO():
    TimeStampISOandLocalTZ = f"{datetime.datetime.now().isoformat(sep='t', timespec='seconds').replace('t', '_T').replace(':', '.')}"
    # TimeStampISOandLocalTZ = f"{nowStart.isoformat(sep='t', timespec='seconds').replace('t', '_T').replace(':', '.')}"
    # TimeStampISOandLocalTZ = (
    #     TimeStampISOandLocalTZ.replace("t", "_T").replace(":", ".")
    #     # f"{date.today().isoformat()}__{int(time.time())}"
    # )
    return f"{TimeStampISOandLocalTZ}"


##################################################################
def get_DS_ISO():
    DateStampToday = (
        f"{date.today().isoformat()}"
        # f"{int(time.time())}_{datetime.datetime.now().isoformat()}"
        # f"{date.today().isoformat()}__{int(time.time())}"
        # f"{datetime.datetime.now().date.isoformat()}"
    )
    return f"{DateStampToday}"


##################################################################
def get_TS_epoch():
    TimeStamp_Epoch = int(time.time())
    return f"{TimeStamp_Epoch}"


##################################################################
TS_ScriptStart_Epoch = get_TS_epoch()
TS_ScriptStart_DS_ISO = get_DS_ISO()
TS_ScriptStart_ISO = get_TS_ISO()
TS_ScriptStart_Full = f"{TS_ScriptStart_Epoch}_{TS_ScriptStart_ISO}"
logScriptPathName = "__archived_sets"

##################################################################


# file = Path("new/directory/foo")
# file.parent.mkdir(parents=True, exist_ok=True)
# file.write_text("toto")
##################################################################
def atomic_write(target_path, content, is_bytes=False):
    dirname = os.path.dirname(target_path)
    mode = "wb" if is_bytes else "w"
    with tempfile.NamedTemporaryFile(mode, dir=dirname, delete=False) as tf:
        tf.write(content)
        temp_name = tf.name
    os.replace(temp_name, target_path)


##################################################################
def log_and_script(action_type, commands, log_message, repo_root):
    log_file = Path(
        f"{repo_root}//{logScriptPathName}//{TS_ScriptStart_Epoch}//{action_type}//{TS_ScriptStart_ISO}__{action_type}.log"
    )
    log_file.parent.mkdir(parents=True, exist_ok=True)

    script_file = Path(
        f"{repo_root}//{logScriptPathName}//{TS_ScriptStart_Epoch}//{action_type}//{TS_ScriptStart_ISO}__{action_type}.sh"
    )
    script_file.parent.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(log_file):
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{get_TS_ISO()}]\n\n")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{log_message}\n")

    if commands:
        if not os.path.exists(script_file):
            with open(script_file, "a", encoding="utf-8") as f:
                f.write("#!/usr/bin/env bash\nset -euo pipefail\n")
                f.write(f"# [{get_TS_ISO()}]\n\n")
                os.chmod(script_file, 0o755)

        with open(script_file, "a", encoding="utf-8") as f:
            for cmd in commands:
                f.writelines(f"{cmd}\n")


##################################################################
def calculate_hash(filepath, algo="sha512"):
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


##################################################################
def get_shard_dir(repo_root, file_hash, shard_depth):
    depth = max(0, min(shard_depth, len(file_hash) // 2))
    path_components = [file_hash[i * 2 : i * 2 + 2] for i in range(depth)]
    return os.path.join(repo_root, *path_components)


##################################################################
def get_file_timestamps(filepath, st=None):
    """
    Extracts all available timestamp and date metadata fields from a file
    (birthtime/creation time, modification time, change time, access time)
    and determines the earliest timestamp.

    Args:
        filepath (str or Path): Path to the target file.
        st (os.stat_result, optional): Pre-existing stat result if available.

    Returns:
        dict: Dictionary containing 'mtime', 'ctime', 'atime', 'birthtime', and 'earliest_time'.
    """
    if st is None:
        try:
            st = os.stat(filepath)
        except OSError:
            return {
                "mtime": 0.0,
                "ctime": 0.0,
                "atime": 0.0,
                "birthtime": None,
                "earliest_time": 0.0,
            }

    mtime = float(st.st_mtime)
    ctime = float(getattr(st, "st_ctime", st.st_mtime))
    atime = float(getattr(st, "st_atime", st.st_mtime))
    birthtime = None

    if hasattr(st, "st_birthtime"):
        try:
            b = float(st.st_birthtime)
            if b > 0:
                birthtime = b
        except (AttributeError, ValueError, TypeError):
            pass

    if birthtime is None and sys.platform.startswith("linux"):
        try:
            res = subprocess.run(
                ["stat", "-c", "%W", str(filepath)],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                val = res.stdout.strip()
                if val.isdigit() and int(val) > 0:
                    birthtime = float(val)
        except Exception:
            pass

    candidate_times = [t for t in (birthtime, ctime, mtime) if t is not None and t > 0]
    earliest_time = min(candidate_times) if candidate_times else mtime

    return {
        "mtime": mtime,
        "ctime": ctime,
        "atime": atime,
        "birthtime": birthtime,
        "earliest_time": earliest_time,
    }


def extract_xattrs(filepath, encoding="text", method="local_bin"):
    """
    Extracts and returns all extended attributes of a file using either the
    system binary utility 'getfattr' (default) or Python's os xattr functions.

    Calls getfattr with the -d (dump all extended attributes) and -e
    (encoding: 'text', 'hex', or 'base64') flags, capturing all attributes
    and storing the encoded values as returned for sidecar inclusion.
    When method is 'python', encodes attribute values into the corresponding
    text, hex, or base64 representation.

    Args:
        filepath (str or Path): The path to the file.
        encoding (str): The encoding format for attribute values ('text', 'hex', or 'base64').
                        Default is 'text'.
        method (str): Extraction method: 'local_bin' (default, uses system getfattr utility)
                      or 'python' (uses os.listxattr / os.getxattr).

    Returns:
        dict: A dictionary mapping extended attribute names to their encoded values.
    """
    xattrs = {}

    if method == "local_bin":
        try:
            attrs_raw_output = subprocess.run(
                ["getfattr", "-d", "-m", "-", "-e", encoding, str(filepath)],
                capture_output=True,
                text=True,
                check=False,
            )
            if attrs_raw_output.returncode == 0:
                for line in attrs_raw_output.stdout.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        attr_name, val = line.split("=", 1)
                        xattrs[attr_name.strip()] = val.strip()
                return xattrs, attrs_raw_output
        except (OSError, subprocess.SubprocessError):
            pass

    if method == "python" or not xattrs:
        xattrs = {}
        if not hasattr(os, "listxattr"):
            return xattrs
        try:
            attrs_raw_output = os.listxattr(filepath)
            for attr in attrs_raw_output:
                try:
                    value = os.getxattr(filepath, attr)
                    if encoding == "base64":
                        xattrs[attr] = base64.b64encode(value).decode("ascii")
                    elif encoding == "hex":
                        xattrs[attr] = "0x" + value.hex()
                    elif encoding == "text":
                        xattrs[attr] = value.decode("utf-8", errors="replace")
                    else:
                        xattrs[attr] = str(value)
                except OSError:
                    continue
        except OSError:
            pass
        return (xattrs, attrs_raw_output)

    return (xattrs, attrs_raw_output)


##################################################################


def extract_metadata(filepath):
    st = os.stat(filepath)
    ts = get_file_timestamps(filepath, st)
    meta = {
        "filename": os.path.basename(filepath),
        "path": os.path.abspath(filepath),
        "cataloged_date": get_DS_ISO(),
        "cataloged_timedate_ISO": get_TS_ISO(),
        "cataloged_time_EPOCH": get_TS_epoch(),
        "size": st.st_size,
        "mtime": ts["mtime"],
        "ctime": ts["ctime"],
        "atime": ts["atime"],
        "mode": st.st_mode,
        "earliest_time": ts["earliest_time"],
        "xattrs_txt": extract_xattrs(filepath, "text"),
        "xattrs_hex": extract_xattrs(filepath, "hex"),
        "xattrs_base64": extract_xattrs(filepath, "base64"),
        "xattrs": extract_xattrs(filepath, "text", "python"),
    }
    if ts["birthtime"] is not None:
        meta["birthtime"] = ts["birthtime"]
    return meta


#########################


##################################################################
def set_immutability(filepath, enable=True):
    flag = "+i" if enable else "-i"
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(
                ["sudo chattr", flag, filepath],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass


##################################################################
def perform_link(src, dst, mode):
    if mode == "reflink":
        try:
            res = subprocess.run(
                ["cp", "--reflink=always", src, dst],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            shutil.copy2(src, dst)
            return True
    elif mode == "copy":
        shutil.copy2(src, dst)
        return True
    elif mode == "move":
        shutil.move(src, dst)
        return True
    elif mode == "hardlink":
        os.link(src, dst)
        return True
    elif mode == "symlink":
        os.symlink(os.path.abspath(src), dst)
        return True
    return False


##################################################################
def load_or_init_config(repo_root, args):
    os.makedirs(repo_root, exist_ok=True)
    cfg_path = os.path.join(repo_root, CONFIG_FILE)
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg
    cfg = {
        "algo": args.algo,
        "shard_depth": args.shard_depth,
        "format": args.format,
        "suffix": args.suffix,
    }
    atomic_write(cfg_path, json.dumps(cfg, indent=2))
    return cfg


##################################################################
def migrate_shards(repo_root, new_depth, fmt, suffix):
    for root, dirs, files in os.walk(repo_root):
        for file in files:
            if file.endswith(suffix) or file == CONFIG_FILE:
                continue
            old_path = os.path.join(root, file)
            file_hash = file
            new_dir = get_shard_dir(repo_root, file_hash, new_depth)
            os.makedirs(new_dir, exist_ok=True)
            new_path = os.path.join(new_dir, file)
            if old_path != new_path:
                set_immutability(old_path, False)
                os.rename(old_path, new_path)
                set_immutability(new_path, True)
                old_sidecar = f"{old_path}{suffix}"
                new_sidecar = f"{new_path}{suffix}"
                if os.path.exists(old_sidecar):
                    os.rename(old_sidecar, new_sidecar)


##################################################################
def ingest_file(src, repo_root, cfg, args, registered_blobs=None):
    if not os.path.isfile(src) or os.path.islink(src):
        return
    file_hash = calculate_hash(src, cfg["algo"])
    shard_dir = get_shard_dir(repo_root, file_hash, cfg["shard_depth"])
    os.makedirs(shard_dir, exist_ok=True)
    blob_path = os.path.join(shard_dir, file_hash)
    sidecar_path = f"{blob_path}{cfg['suffix']}"
    meta = extract_metadata(src)
    inst_id = hashlib.new(
        cfg["algo"],
        f"{meta['path']}_{meta['mtime']}_{meta['size']}".encode("utf-8"),
    ).hexdigest()

    #    print(f"Processing: {src} - {meta["size"]} \n")

    if meta["size"] == 0:
        print(f"Skipping: {src} because filesize is {meta['size']} \n")

        log_and_script(
            "skipped",
            [],
            f"Skipped zero size file: {src}",
            repo_root,
        )
        return
    else:
        print(f"Processing: {src} - {meta['size']} \n")
        sidecar_data = sidecar_read(sidecar_path, cfg["format"]) or {
            "hash": file_hash,
            "algorithm": cfg["algo"],
            "instances": {},
        }
        sidecar_data["instances"][inst_id] = meta

        quoted_src = shlex.quote(src)
        quoted_blob = shlex.quote(blob_path)
        quoted_shard = shlex.quote(shard_dir)
        quoted_abs_src = shlex.quote(os.path.abspath(src))
        force = getattr(args, "force", False)

        is_registered = registered_blobs is not None and file_hash in registered_blobs
        blob_exists = os.path.exists(blob_path) or is_registered

        if not blob_exists:
            if registered_blobs is not None:
                registered_blobs.add(file_hash)

            cmds = [f"mkdir -p {quoted_shard}"]
            if args.link_mode == "reflink":
                cmds.append(
                    f"cp --reflink=always {quoted_src} {quoted_blob} 2>/dev/null || cp -a {quoted_src} {quoted_blob}"
                )
            elif args.link_mode == "copy":
                cmds.append(f"cp -a {quoted_src} {quoted_blob}")
            elif args.link_mode == "move":
                cmds.append(f"mv {quoted_src} {quoted_blob}")
            elif args.link_mode == "hardlink":
                cmds.append(f"ln {quoted_src} {quoted_blob}")
            elif args.link_mode == "symlink":
                cmds.append(f"ln -s {quoted_abs_src} {quoted_blob}")

            if args.link_mode != "symlink":
                cmds.append(f"chattr +i {quoted_blob} 2>/dev/null || true")

            sidecar_write(sidecar_path, sidecar_data, cfg["format"])
            log_and_script(
                "ingest",
                cmds,
                f"Ingested new blob: {file_hash} from {src}"
                + (" [FORCED]" if force else " [SCRIPTED]"),
                repo_root,
            )
            if force:
                perform_link(src, blob_path, args.link_mode)
                if args.link_mode != "symlink":
                    set_immutability(blob_path, True)
        else:
            existing_earliest_time = None
            if sidecar_data and "instances" in sidecar_data:
                inst_times = [
                    inst.get("earliest_time")
                    or inst.get("birthtime")
                    or inst.get("mtime")
                    for inst in sidecar_data["instances"].values()
                    if (
                        inst.get("earliest_time")
                        or inst.get("birthtime")
                        or inst.get("mtime")
                    )
                ]
                if inst_times:
                    existing_earliest_time = min(inst_times)
            if existing_earliest_time is None and os.path.exists(blob_path):
                existing_earliest_time = get_file_timestamps(blob_path)["earliest_time"]
            if existing_earliest_time is None:
                existing_earliest_time = meta["earliest_time"]

            new_file_earliest = meta.get("earliest_time", meta["mtime"])

            if new_file_earliest < existing_earliest_time:
                origin_cmds = []
                if args.link_mode != "symlink":
                    origin_cmds.append(f"chattr -i {quoted_blob} 2>/dev/null || true")
                if args.link_mode == "reflink":
                    origin_cmds.append(
                        f"cp --reflink=always {quoted_src} {quoted_blob} 2>/dev/null || cp -a {quoted_src} {quoted_blob}"
                    )
                elif args.link_mode == "copy":
                    origin_cmds.append(f"cp -a {quoted_src} {quoted_blob}")
                elif args.link_mode == "move":
                    origin_cmds.append(f"mv {quoted_src} {quoted_blob}")
                elif args.link_mode == "hardlink":
                    origin_cmds.append(f"ln -f {quoted_src} {quoted_blob}")
                elif args.link_mode == "symlink":
                    origin_cmds.append(f"ln -sf {quoted_abs_src} {quoted_blob}")
                if args.link_mode != "symlink":
                    origin_cmds.append(f"chattr +i {quoted_blob} 2>/dev/null || true")

                log_and_script(
                    f"duplicates-with-earlier-origin//{file_hash}",
                    origin_cmds,
                    f"Updated origin for\n{file_hash} with\n {src}\n  -[existing earliest: {existing_earliest_time}]\n  -[new file earliest: {new_file_earliest}] ",
                    repo_root,
                )
                if force:
                    if args.link_mode != "symlink":
                        set_immutability(blob_path, False)
                    perform_link(src, blob_path, args.link_mode)
                    if args.link_mode != "symlink":
                        set_immutability(blob_path, True)

            sidecar_write(sidecar_path, sidecar_data, cfg["format"])
            handle_dedup(src, blob_path, args, repo_root)


##################################################################
def handle_dedup(src, blob_path, args, repo_root):
    mode = args.dedup_mode
    force = getattr(args, "force", False)
    quoted_src = shlex.quote(src)
    quoted_blob = shlex.quote(blob_path)
    cmds = []

    if mode == "ignore":
        log_and_script(
            "dedup", [], f"Duplicate found for {src}. Action: Ignore", repo_root
        )
    elif mode == "delete":
        cmds.append(f"rm -vf {quoted_src}")
        log_and_script(
            "dedup",
            cmds,
            f"Duplicate found for {src}. Action: Delete"
            + (" [FORCED]" if force else " [SCRIPTED]"),
            repo_root,
        )
        if force:
            try:
                os.remove(src)
            except OSError:
                pass
    elif mode == "hardlink":
        cmds.append(f"ln -vf {quoted_blob} {quoted_src}")
        log_and_script(
            "dedup",
            cmds,
            f"Duplicate found for {src}. Action: Hardlink"
            + (" [FORCED]" if force else " [SCRIPTED]"),
            repo_root,
        )
        if force:
            try:
                os.remove(src)
                os.link(blob_path, src)
            except OSError:
                pass
    elif mode == "softlink":
        cmds.append(f"ln -sf {quoted_blob} {quoted_src}")
        log_and_script(
            "dedup",
            cmds,
            f"Duplicate found for {src}. Action: Softlink"
            + (" [FORCED]" if force else " [SCRIPTED]"),
            repo_root,
        )
        if force:
            try:
                os.remove(src)
                os.symlink(os.path.abspath(blob_path), src)
            except OSError:
                pass


##################################################################


##################################################################
def sidecar_write(sidecar_path, data, fmt="json"):
    if fmt == "json":
        content = json.dumps(data, indent=2)
        atomic_write(sidecar_path, content, is_bytes=False)
    else:
        root = XmlTree.Element("entry")
        XmlTree.SubElement(root, "hash").text = data.get("hash", "")
        XmlTree.SubElement(root, "algorithm").text = data.get("algorithm", "")
        known_as = XmlTree.SubElement(root, "known_as")
        for inst_id, inst in data.get("instances", {}).items():
            inst_el = XmlTree.SubElement(known_as, "instance", id=inst_id)
            for k, v in inst.items():
                if isinstance(v, dict):
                    x_el = XmlTree.SubElement(inst_el, k)
                    for xk, xv in v.items():
                        XmlTree.SubElement(x_el, "xattr", name=xk).text = (
                            str(xv) if xv is not None else ""
                        )
                else:
                    XmlTree.SubElement(inst_el, k).text = str(v)
        tree = XmlTree.ElementTree(root)
        XmlTree.indent(tree, space="  ")
        dirname = os.path.dirname(sidecar_path)
        with tempfile.NamedTemporaryFile("wb", dir=dirname, delete=False) as tf:
            tree.write(tf, encoding="utf-8", xml_declaration=True)
            temp_name = tf.name
        os.replace(temp_name, sidecar_path)


##################################################################
def sidecar_read(sidecar_path, fmt="json"):
    """
    Reads a Sidecar JSON or XML file.

    Parameters:
    - sidecar_path (str): The file system path to the Sidecar file.
    - fmt (str): The format of the Sidecar file, either 'json' or 'xml'.

    Returns:
    - dict: A dictionary containing the parsed data from the Sidecar file.
            If the file does not exist, returns None.
    """

    if not os.path.exists(sidecar_path):
        return None
    if fmt == "json":
        with open(sidecar_path, "r", encoding="utf-8") as f:
            return json.load(f)

    else:
        tree = XmlTree.parse(sidecar_path)
        root = tree.getroot()
        data = {
            "hash": root.findtext("hash", ""),
            "algorithm": root.findtext("algorithm", ""),
            "instances": {},
        }
        known_as = root.find("known_as")
        if known_as is not None:
            for inst in known_as.findall("instance"):
                inst_id = inst.get("id")
                inst_data = {}
                for child in inst:
                    if (
                        child.tag == "xattrs"
                        or child.tag.startswith("xattrs")
                        or len(child.findall("xattr")) > 0
                    ):
                        inst_data[child.tag] = {
                            x.get("name"): x.text for x in child.findall("xattr")
                        }
                    elif child.tag in ("size", "mode"):
                        inst_data[child.tag] = int(child.text)
                    elif child.tag in (
                        "mtime",
                        "ctime",
                        "atime",
                        "birthtime",
                        "earliest_time",
                    ):
                        inst_data[child.tag] = float(child.text)
                    else:
                        inst_data[child.tag] = child.text
                data["instances"][inst_id] = inst_data
        return data


##################################################################
def parse_arguments():
    parser = argparse.ArgumentParser(description="ezCAS Storage Utility")
    parser.add_argument("repo", help="Path to CAS Repository")
    parser.add_argument("files", nargs="*", help="Files to ingest")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recursive ingestion"
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Execute ingestion and dedup actions directly; by default only logs and creates ingest script",
    )
    parser.add_argument("--algo", choices=["sha256", "sha512"], default="sha512")
    parser.add_argument("--format", choices=["xml", "json"], default="xml")
    parser.add_argument("--suffix", default=".known-as")
    parser.add_argument(
        "--link-mode",
        choices=["reflink", "hardlink", "symlink", "copy", "move"],
        default="reflink",
    )
    parser.add_argument(
        "--dedup-mode",
        choices=["ignore", "delete", "hardlink", "softlink"],
        default="ignore",
    )
    parser.add_argument("--shard-depth", type=int, default=2)
    parser.add_argument("--migrate-shards", action="store_true")
    return parser.parse_args()


##################################################################
##################################################################


def get_safe_size(filepath):
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


##################################################################
def group_and_sort_targets(targets, repo_root=None):
    """
    Groups target files by identical filesize and sorts the groups by size.
    Within each identical filesize group, files are sorted by their earliest
    timestamp (earliest created/modified first).
    Zero-byte filegroups are identified and skipped with appropriate logging.

    Args:
        targets (iterable): Iterable of file paths to group and sort.
        repo_root (str, optional): CAS repository root path for logging skipped files.

    Returns:
        list of tuple: A list of (filesize, list_of_filepaths) sorted by filesize ascending,
                       with files in each group sorted earliest timestamp first.
    """
    size_groups = {}
    for t in targets:
        if not os.path.isfile(t) or os.path.islink(t):
            continue
        sz = get_safe_size(t)
        size_groups.setdefault(sz, []).append(t)

    # Skip zero-byte filegroup
    if 0 in size_groups:
        zero_files = size_groups.pop(0)
        print(f"Skipping {len(zero_files)} zero-byte file(s) in zero-size group\n")
        if repo_root:
            log_and_script(
                "skipped",
                [],
                f"Skipped zero size filegroup ({len(zero_files)} files):\n"
                + "\n".join(zero_files),
                repo_root,
            )

    def get_safe_earliest_time(filepath):
        return get_file_timestamps(filepath)["earliest_time"]

    sorted_groups = []
    for sz in sorted(size_groups.keys()):
        files = size_groups[sz]
        files.sort(key=get_safe_earliest_time)
        sorted_groups.append((sz, files))

    return sorted_groups


def ingest_file_group(file_group, repo_root, cfg, args, registered_blobs=None):
    """
    Processes a group of files sharing identical filesize together,
    ordered by earliest timestamp first to optimize deduplication
    and discovery/storage of the earliest created file.

    Args:
        file_group (list): List of file paths with identical size, sorted earliest first.
        repo_root (str): CAS repository root.
        cfg (dict): CAS configuration dict.
        args (Namespace): CLI parsed arguments.
        registered_blobs (set, optional): Set of blob hashes seen/registered in current session.
    """
    if not file_group:
        return

    log_and_script(
        "identical-filesize-group",
        [],
        f"Processing group with size {get_safe_size(file_group[0])} bytes ({len(file_group)} files):\n"
        + "\n".join(file_group),
        repo_root,
    )

    for target in file_group:
        ingest_file(target, repo_root, cfg, args, registered_blobs=registered_blobs)


##################################################################


def main():
    args = parse_arguments()
    cfg = load_or_init_config(args.repo, args)

    if args.migrate_shards:
        migrate_shards(args.repo, args.shard_depth, args.format, args.suffix)
        cfg["shard_depth"] = args.shard_depth
        atomic_write(os.path.join(args.repo, CONFIG_FILE), json.dumps(cfg, indent=2))
        return

    targets = set()
    for f in args.files:
        if os.path.isdir(f) and args.recursive:
            for root, _, filenames in os.walk(f):
                for fn in filenames:
                    targets.add(os.path.join(root, fn))
        elif os.path.isfile(f):
            targets.add(f)

    # Group and sort target files:
    # 1. Group targets having identical filesize
    # 2. Skip zero-byte filegroups
    # 3. Sort filegroups by filesize, and within each group sort earliest-first
    grouped_targets = group_and_sort_targets(targets, repo_root=args.repo)

    all_sorted_targets = []
    for _, file_group in grouped_targets:
        all_sorted_targets.extend(file_group)

    log_and_script(
        "sorted-target-files",
        [],
        f"{all_sorted_targets}",
        args.repo,
    )

    # Shared set to track blobs registered in current ingestion session
    registered_blobs = set()

    for size, file_group in grouped_targets:
        ingest_file_group(
            file_group, args.repo, cfg, args, registered_blobs=registered_blobs
        )


##################################################################

if __name__ == "__main__":
    main()
