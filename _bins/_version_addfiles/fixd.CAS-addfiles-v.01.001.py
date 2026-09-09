#!/usr/bin/env python3
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


# TODO: ADD / TEST SOME CHECKS WHEN INJESTING AND VALIDATING DUPLICATES WHEN IN CAS ITEM IS SYMLINK. EITHER REFUSE TO REMOVE DUPLICATE THAT POINTS TO SYMLINK IN CAS, OR RESOLVE SYMLINK INTO A FILE/HARDLINK FIRST, THEN DEDUPE.
# TESTED: DEDUPE/INGEST SYMLINK/SYMLINK FAILS IF NEW,
# TESTED: ADD VIA HARDLINK OR ALREADY IN CAS, copy as reflink fails due to file existing. force does not work either. Must rm file first bug? not sure
# TSiso={datetime.now().isoformat()}
epoch_time = time.time()
CONFIG_FILE = ".CAS-config"
DEFAULT_SIDECAR_SUFFIX = ".known-as"
DEDUP_SCRIPT = f"CAS-dedupActionlist_{epoch_time}.sh"


def get_file_xattrs(filepath: Path) -> Dict[str, str]:
    attrs = {}
    try:
        names = os.listxattr(filepath, follow_symlinks=False)
        for name in names:
            try:
                val = os.getxattr(filepath, name, follow_symlinks=False)
                attrs[name] = base64.b64encode(val).decode("utf-8")
            except OSError:
                continue
    except (AttributeError, OSError):
        pass
    return attrs


def calculate_hash(filepath: Path, algo: str, use_external: bool) -> str:
    if use_external:
        cmd = f"{algo}sum"
        res = subprocess.check_output([cmd, str(filepath)]).decode().strip()
        return res.split()[0]

    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def load_sidecar(path: Path, fmt: str) -> Dict[str, Any]:
    if fmt == "json":
        with open(path, "r") as f:
            return json.load(f)

    tree = ET.parse(path)
    root = tree.getroot()
    data = {
        "hash": root.find("hash").text,
        "algorithm": root.find("algorithm").text,
        "known_as": {},
    }
    for inst in root.find("known_as"):
        meta = {}
        for child in inst:
            if child.tag == "xattrs":
                meta["xattrs"] = {x.attrib["key"]: x.text for x in child}
            else:
                meta[child.tag] = child.text
        data["known_as"][inst.get("id")] = meta
    return data


def save_sidecar(path: Path, data: Dict[str, Any], fmt: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return

    root = ET.Element("entry")
    ET.SubElement(root, "hash").text = data["hash"]
    ET.SubElement(root, "algorithm").text = data["algorithm"]
    ka = ET.SubElement(root, "known_as")
    for pid, meta in data["known_as"].items():
        inst = ET.SubElement(ka, "instance", id=pid)
        for k, v in meta.items():
            if k == "xattrs":
                x_node = ET.SubElement(inst, "xattrs")
                for x_key, x_val in v.items():
                    sub = ET.SubElement(x_node, "attr", key=x_key)
                    sub.text = str(x_val)
            else:
                ET.SubElement(inst, k).text = str(v)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def get_storage_path(repo: Path, file_hash: str, depth: int) -> Path:
    if depth == 0:
        return repo / file_hash
    parts = [file_hash[i * 2 : i * 2 + 2] for i in range(depth)]
    return repo.joinpath(*parts) / file_hash


def get_metadata(filepath: Path) -> tuple[str, Dict[str, Any]]:
    stat = filepath.stat()
    path_id = hashlib.sha256(str(filepath).encode()).hexdigest()
    meta = {
        "path": str(filepath),
        "ingested_at": datetime.now().isoformat(),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mode": oct(stat.st_mode)[-3:],
        "xattrs": get_file_xattrs(filepath),
    }
    return path_id, meta


def run_dedupe_action(src: Path, dst: Path, action: str):
    if action == "ignore":
        return
    if action == "hardlink":
        subprocess.run(
            ["ln", "-vf", str(dst), str(src)], check=True, capture_output=True
        )
    elif action == "symlink":
        subprocess.run(
            ["ln", "-vsf", str(dst), str(src)], check=True, capture_output=True
        )
    elif action == "reflink":
        # Edge case with hardlinked files need to remove before reflinking them as they are same file.
        os.remove(src)
        subprocess.run(
            [
                "cp",
                "-v",
                "-f",
                "--preserve=all",
                "--reflink=always",
                str(dst),
                str(src),
            ],
            check=True,
            capture_output=True,
        )
    elif action == "delete":
        os.remove(src)


def log_dedupe(src: Path, dst: Path, action: str, force: bool):
    if action == "ignore":
        entry = f"# Duplicate: {src}\n{cmds.get(action, '')}"
        with open(DEDUP_SCRIPT, "a") as f:
            f.write(entry)
        return
    q_src, q_dst = shlex.quote(str(src)), shlex.quote(str(dst))
    cmds = {
        "hardlink": f"ln -vf {q_dst} {q_src}\n",
        "symlink": f"ln -vsf {q_dst} {q_src}\n",
        "reflink": f"rm -vf {q_src} && cp -v -f --preserve=all --reflink=always {q_dst} {q_src}\n",
        "delete": f"rm -fv {q_src}\n",
    }
    entry = f"# Duplicate: {src}\n{cmds.get(action, '')}"
    if force:
        entry += f"# Force enabled: {action} performed.\n"
        run_dedupe_action(src, dst, action)
    with open(DEDUP_SCRIPT, "a") as f:
        f.write(entry)


def ingest_file(src: Path, conf: Dict[str, Any]):
    try:
        f_hash = calculate_hash(src, conf["algo"], conf["use_external"])
        cas_path = get_storage_path(conf["repo"], f_hash, conf["shard_depth"])
        sidecar_path = cas_path.parent / (cas_path.name + conf["suffix"])
        is_dup = cas_path.exists()
        p_id, meta = get_metadata(src)

        if not is_dup:
            cas_path.parent.mkdir(parents=True, exist_ok=True)
            meth = conf["ingest_method"]
            if meth == "reflink":
                subprocess.run(
                    [
                        "cp",
                        "--preserve=all",
                        "--reflink=always",
                        str(src),
                        str(cas_path),
                    ],
                    check=True,
                )
            elif meth == "move":
                if conf["dedupe_action"] in ["ignore", "delete"] and not conf["force"]:
                    print(f"ERR: Move + {conf['dedupe_action']} requires --force")
                    return
                subprocess.run(["mv", "-vn", str(src), str(cas_path)], check=True)
                run_dedupe_action(src, cas_path, conf["dedupe_action"])
            elif meth == "hardlink":
                os.link(src, cas_path)
            elif meth == "symlink":
                os.symlink(src, cas_path)

        data = (
            load_sidecar(sidecar_path, conf["format"])
            if sidecar_path.exists()
            else {"hash": f_hash, "algorithm": conf["algo"], "known_as": {}}
        )

        data["known_as"][p_id] = meta
        save_sidecar(sidecar_path, data, conf["format"])

        if is_dup:
            print(f"DUPLICATE -> {f_hash[:8]}... ({src})")
            log_dedupe(src, cas_path, conf["dedupe_action"], conf["force"])
        else:
            print(f"OK -> {f_hash[:8]}... ({src})")
    except Exception as e:
        print(f"ERR {src}: {e}")


def migrate_structure(conf: Dict[str, Any]):
    repo = conf["repo"]
    for item in repo.rglob("*"):
        if not item.is_file() or item.name in [CONFIG_FILE, DEDUP_SCRIPT]:
            continue
        f_hash = (
            item.name[: -len(conf["suffix"])]
            if item.name.endswith(conf["suffix"])
            else item.name
        )
        target = get_storage_path(repo, f_hash, conf["shard_depth"])
        if item.name.endswith(conf["suffix"]):
            target = target.parent / (target.name + conf["suffix"])
        if item.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(item, target)
    for root, dirs, _ in os.walk(repo, topdown=False):
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass


def resolve_config(args: argparse.Namespace) -> Dict[str, Any]:
    repo = Path(args.repo).resolve()
    repo.mkdir(parents=True, exist_ok=True)
    cfg_path = repo / CONFIG_FILE
    saved = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}

    conf = vars(args)
    conf["repo"] = repo
    for k, v in saved.items():
        if getattr(args, k) == args_parser.get_default(k):
            conf[k] = v

    keys = [
        "algo",
        "use_external",
        "format",
        "ingest_method",
        "dedupe_action",
        "shard_depth",
    ]
    cfg_path.write_text(json.dumps({k: conf[k] for k in keys}))
    return conf


def expand_paths(paths: list, recursive: bool) -> Generator[Path, None, None]:
    for p_str in paths:
        p = Path(p_str)
        if p.is_symlink():
            continue
        res = p.resolve()
        if res.is_file():
            yield res
        elif res.is_dir() and recursive:
            for sub in res.rglob("*"):
                if not sub.is_symlink() and sub.is_file():
                    yield sub


args_parser = argparse.ArgumentParser()
args_parser.add_argument("repo")
args_parser.add_argument("files", nargs="*")
args_parser.add_argument("-r", "--recursive", action="store_true")
args_parser.add_argument("-f", "--force", action="store_true")
args_parser.add_argument("--algo", default="sha512", choices=["sha512", "sha256"])
args_parser.add_argument("--use-external", action="store_true")
args_parser.add_argument("--format", default="xml", choices=["xml", "json"])
args_parser.add_argument("--suffix", default="DEFAULT_SIDECAR_SUFFIX")
args_parser.add_argument(
    "--ingest-method",
    default="hardlink",
    choices=["reflink", "hardlink", "symlink", "copy", "move"],
)
args_parser.add_argument(
    "--dedupe-action",
    default="ignore",
    choices=["ignore", "delete", "hardlink", "symlink", "reflink"],
)
args_parser.add_argument("--shard-depth", type=int, default=2)
args_parser.add_argument("--migrate-shards", action="store_true")

if __name__ == "__main__":
    cli_args = args_parser.parse_args()
    config = resolve_config(cli_args)

    with open(DEDUP_SCRIPT, "a") as f:
        if f.tell() == 0:
            f.write("#!/bin/bash\n")
        f.write(f"\n# Run {datetime.now().isoformat()}\n# Args: {sys.argv}\n")

    if config["migrate_shards"]:
        migrate_structure(config)

    for f_path in expand_paths(config["files"], config["recursive"]):
        ingest_file(f_path, config)
