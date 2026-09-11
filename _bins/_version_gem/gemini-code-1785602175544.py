#!/usr/bin/env python3
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
import xml.etree.ElementTree as XmlTree
from pathlib import Path

CONFIG_FILE = ".CAS_datastore.config"

# CHANGELOG
# SKIP ZERO BYTE FILES
# INSTANCE TS ONE TIME FOR LOGGING
# RENAME ET import to XmlTree


def get_TS_ISO():
    TimeStampISOandLocalTZ = f"{int(time.time())}_{datetime.datetime.now().isoformat()}"
    return f"{TimeStampISOandLocalTZ}"


def get_TS_epoch():
    TimeStamp_Epoch = int(time.time())
    return f"{TimeStamp_Epoch}"


TS_ScriptStart_Epoch = get_TS_epoch()
TS_ScriptStart_ISO = get_TS_ISO()
TS_ScriptStart_Full = f"{TS_ScriptStart_Epoch}_{TS_ScriptStart_ISO}"
logScriptPathName = "__archived_sets"

# file = Path("new/directory/foo")
# file.parent.mkdir(parents=True, exist_ok=True)
# file.write_text("toto")


def log_and_script(action_type, commands, log_message, repo_root):
    log_file = Path(
        f"{repo_root}//{logScriptPathName}//{TS_ScriptStart_Epoch}//{action_type}//{TS_ScriptStart_ISO}__{action_type}.log"
    )
    log_file.parent.mkdir(parents=True, exist_ok=True)

    script_file = Path(
        f"{repo_root}//{logScriptPathName}//{TS_ScriptStart_Epoch}//{action_type}//{TS_ScriptStart_ISO}__{action_type}.sh"
    )
    script_file.parent.mkdir(parents=True, exist_ok=True)

    #    script_file = os.path.join(repo_root,"/",f"{TS_ScriptStart_Epoch}","/",f"{TS_ScriptStart_Full}","__",{action_type}.sh,)

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


def calculate_hash(filepath, algo="sha512"):
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_shard_dir(repo_root, file_hash, shard_depth):
    depth = max(0, min(shard_depth, len(file_hash) // 2))
    path_components = [file_hash[i * 2 : i * 2 + 2] for i in range(depth)]
    return os.path.join(repo_root, *path_components)


def extract_xattrs(filepath):
    xattrs = {}
    if not hasattr(os, "listxattr"):
        return xattrs
    try:
        attrs = os.listxattr(filepath)
        for attr in attrs:
            try:
                val = os.getxattr(filepath, attr)
                xattrs[attr] = base64.b64encode(val).decode("ascii")
            except OSError:
                continue
    except OSError:
        pass
    return xattrs


def extract_metadata(filepath):
    st = os.stat(filepath)
    return {
        "path": os.path.abspath(filepath),
        "ingested_at": get_TS_ISO(),
        "size": st.st_size,
        "mtime": st.st_mtime,
        "ctime": getattr(st, "st_ctime", st.st_mtime),
        "mode": st.st_mode,
        "xattrs": extract_xattrs(filepath),
    }


def set_immutability(filepath, enable=True):
    flag = "+i" if enable else "-i"
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(
                ["chattr", flag, filepath],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass


def atomic_write(target_path, content, is_bytes=False):
    dirname = os.path.dirname(target_path)
    mode = "wb" if is_bytes else "w"
    with tempfile.NamedTemporaryFile(mode, dir=dirname, delete=False) as tf:
        tf.write(content)
        temp_name = tf.name
    os.replace(temp_name, target_path)


def write_sidecar(sidecar_path, data, fmt="json"):
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
                if k == "xattrs":
                    x_el = XmlTree.SubElement(inst_el, "xattrs")
                    for xk, xv in v.items():
                        XmlTree.SubElement(x_el, "xattr", name=xk).text = xv
                else:
                    XmlTree.SubElement(inst_el, k).text = str(v)
        tree = XmlTree.ElementTree(root)
        XmlTree.indent(tree, space="  ")
        dirname = os.path.dirname(sidecar_path)
        with tempfile.NamedTemporaryFile("wb", dir=dirname, delete=False) as tf:
            tree.write(tf, encoding="utf-8", xml_declaration=True)
            temp_name = tf.name
        os.replace(temp_name, sidecar_path)


def read_sidecar(sidecar_path, fmt="json"):
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
                    if child.tag == "xattrs":
                        inst_data["xattrs"] = {
                            x.get("name"): x.text for x in child.findall("xattr")
                        }
                    elif child.tag in ("size", "mode"):
                        inst_data[child.tag] = int(child.text)
                    elif child.tag in ("mtime", "ctime"):
                        inst_data[child.tag] = float(child.text)
                    else:
                        inst_data[child.tag] = child.text
                data["instances"][inst_id] = inst_data
        return data


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


def ingest_file(src, repo_root, cfg, args):
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
        sidecar_data = read_sidecar(sidecar_path, cfg["format"]) or {
            "hash": file_hash,
            "algorithm": cfg["algo"],
            "instances": {},
        }
        sidecar_data["instances"][inst_id] = meta

        if not os.path.exists(blob_path):
            perform_link(src, blob_path, args.link_mode)
            if args.link_mode != "symlink":
                set_immutability(blob_path, True)
            write_sidecar(sidecar_path, sidecar_data, cfg["format"])
            log_and_script(
                "ingest",
                [],
                f"Ingested new blob: {file_hash} from {src}",
                repo_root,
            )
        else:
            existing_mtime = os.stat(blob_path).st_mtime
            if meta["mtime"] < existing_mtime:
                # set_immutability(blob_path, False)
                # perform_link(src, blob_path, args.link_mode)
                # set_immutability(blob_path, True)
                log_and_script(
                    f"duplicates-with-earlier-origin//{file_hash}",
                    [],
                    f"Updated origin for\n{file_hash} with\n {src}\n  -[{existing_mtime}]\n  -[{meta['mtime']}] ",
                    repo_root,
                )
            write_sidecar(sidecar_path, sidecar_data, cfg["format"])
            handle_dedup(src, blob_path, args, repo_root)


def handle_dedup(src, blob_path, args, repo_root):
    mode = args.dedup_mode
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
            f"Duplicate found for {src}. Action: Delete",
            repo_root,
        )
        # os.remove(src)
    elif mode == "hardlink":
        cmds.append(f"ln -vf {quoted_blob} {quoted_src}")
        log_and_script(
            "dedup",
            cmds,
            f"Duplicate found for {src}. Action: Hardlink",
            repo_root,
        )
        # os.remove(src)
        # os.link(blob_path, src)
    elif mode == "softlink":
        cmds.append(f"ln -sf {quoted_blob} {quoted_src}")
        log_and_script(
            "dedup",
            cmds,
            f"Duplicate found for {src}. Action: Softlink",
            repo_root,
        )
        # os.remove(src)
        # os.symlink(blob_path, src)


def main():
    parser = argparse.ArgumentParser(description="ezCAS Storage Utility")
    parser.add_argument("repo", help="Path to CAS Repository")
    parser.add_argument("files", nargs="*", help="Files to ingest")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recursive ingestion"
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

    args = parser.parse_args()
    cfg = load_or_init_config(args.repo, args)

    if args.migrate_shards:
        migrate_shards(args.repo, args.shard_depth, cfg["format"], cfg["suffix"])
        cfg["shard_depth"] = args.shard_depth
        atomic_write(os.path.join(args.repo, CONFIG_FILE), json.dumps(cfg, indent=2))
        return

    def get_safe_size(filepath):
        try:
            return os.path.getsize(filepath)
        except OSError:
            return 0

    targets = set()
    for f in args.files:
        if os.path.isdir(f) and args.recursive:
            for root, _, filenames in os.walk(f):
                for fn in filenames:
                    targets.add(os.path.join(root, fn))
        elif os.path.isfile(f):
            targets.add(f)

    sorted_targets = sorted(list(targets), key=get_safe_size)

    log_and_script(
        "sorted-target-files",
        [],
        f"{sorted_targets}",
        args.repo,
    )

    for target in sorted_targets:
        ingest_file(target, args.repo, cfg, args)

    # targets = []
    # for f in args.files:
    #     if os.path.isdir(f) and args.recursive:
    #         for root, _, filenames in os.walk(f):
    #             for fn in filenames:
    #                 targets.append(os.path.join(root, fn))
    #     elif os.path.isfile(f):
    #         targets.append(f)

    # for target in targets:
    #     ingest_file(target, args.repo, cfg, args)


if __name__ == "__main__":
    main()
