#!/usr/bin/env python3
import os
import sys
import hashlib
import json
import argparse
import subprocess
import shutil
import platform
import shlex
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict

# --- Configuration & Constants ---
CONFIG_FILE = ".CAS-config"
DEFAULT_SIDECAR_SUFFIX = ".known-as"
DEDUP_SCRIPT = "fixd_dedup_actions.sh"


# --- Helper Functions (XATTRs) ---
def get_raw_xattrs(filepath: Path) -> Dict[str, str]:
    """Retrieves raw xattrs and returns them as Base64 encoded strings."""
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


# --- Hashing Strategies ---
class Hasher:
    def calculate(self, filepath):
        raise NotImplementedError


class InternalHasher(Hasher):
    def __init__(self, alg_name):
        self.alg_name = alg_name

    def calculate(self, filepath):
        h = hashlib.new(self.alg_name)
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()


class ExternalHasher(Hasher):
    def __init__(self, alg_name):
        self.cmd = f"{alg_name}sum"

    def calculate(self, filepath):
        res = subprocess.check_output([self.cmd, filepath]).decode().strip()
        return res.split()[0]


# --- Sidecar Strategies ---
class SidecarHandler:
    def load(self, path):
        raise NotImplementedError

    def save(self, path, data):
        raise NotImplementedError

    def create_empty(self, file_hash, algo):
        raise NotImplementedError


class JSONHandler(SidecarHandler):
    def load(self, path):
        with open(path, "r") as f:
            return json.load(f)

    def save(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def create_empty(self, file_hash, algo):
        return {"hash": file_hash, "algorithm": algo, "known_as": {}}


class XMLHandler(SidecarHandler):
    def load(self, path):
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
                    x_dict = {}
                    for x in child:
                        x_dict[x.attrib["key"]] = x.text
                    meta["xattrs"] = x_dict
                else:
                    meta[child.tag] = child.text
            data["known_as"][inst.get("id")] = meta
        return data

    def save(self, path, data):
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

    def create_empty(self, file_hash, algo):
        return {"hash": file_hash, "algorithm": algo, "known_as": {}}


# --- Core Logic ---
class CASIngestor:
    def __init__(self, args):
        self.repo = Path(args.repo).resolve()
        self.repo.mkdir(parents=True, exist_ok=True)
        self.args = self._resolve_config(args)
        self.hasher = self._get_hasher()
        self.sidecar_handler = (
            XMLHandler() if self.args.format == "xml" else JSONHandler()
        )

    def _resolve_config(self, args):
        config_path = self.repo / CONFIG_FILE
        saved_opts = {}
        if config_path.exists():
            with open(config_path, "r") as f:
                saved_opts = json.load(f)

        final_ns = argparse.Namespace(**vars(args))

        if saved_opts:
            for k, v in saved_opts.items():
                if getattr(args, k) == getattr(args_parser.get_default(k), k, None):
                    setattr(final_ns, k, v)

        with open(config_path, "w") as f:
            opts = {
                k: getattr(final_ns, k)
                for k in ["algo", "use_external", "format", "link_mode", "shard_depth"]
            }
            json.dump(opts, f)

        return final_ns

    def _get_hasher(self):
        algo = self.args.algo
        if self.args.use_external:
            return ExternalHasher(algo)
        return InternalHasher(algo)

    def _get_storage_path(self, file_hash):
        if self.args.shard_depth == 0:
            return self.repo / file_hash
        parts = []
        for i in range(self.args.shard_depth):
            start = i * 2
            parts.append(file_hash[start : start + 2])
        return self.repo.joinpath(*parts) / file_hash

    def _get_metadata(self, filepath):
        stat = os.stat(filepath)
        path_id = hashlib.sha256(str(filepath).encode()).hexdigest()

        xattrs_data = get_raw_xattrs(filepath)

        meta = {
            "path": str(filepath),
            "ingested_at": datetime.now().isoformat(),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "mode": oct(stat.st_mode)[-3:],
            "xattrs": xattrs_data,
        }
        return path_id, meta

    # def _reflink_copy(self, src, dst):
    #     if dst.exists(): return
    #     dst.parent.mkdir(parents=True, exist_ok=True)
    #     try:
    #         if platform.system() == 'Darwin':
    #             os.clonefile(src, dst)
    #         else:
    #             subprocess.run(['cp', '--reflink=always', src, dst],
    #                          check=True, capture_output=True)
    #     except (OSError, subprocess.CalledProcessError) as e:
    #         if self.args.link_mode == 'reflink': raise Exception(f"Reflink failed: {e}")
    #         elif self.args.link_mode == 'hardlink': os.link(src, dst)
    #         elif self.args.link_mode == 'symlink': os.symlink(src, dst)
    #         else: shutil.copy2(src, dst)

    def _ingest_method(self, src, dst):
        if dst.exists():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if platform.system() == "Darwin":
                os.clonefile(src, dst)
            else:
                if self.args.link_mode == "reflink":
                    subprocess.run(
                        ["cp", "--preserve=all --reflink=always", src, dst],
                        check=True,
                        capture_output=True,
                    )

                elif self.args.link_mode == "hardlink":
                    os.link(src, dst)
                elif self.args.link_mode == "symlink":
                    os.symlink(src, dst)
                else:
                    shutil.copy2(src, dst)

        except (OSError, subprocess.CalledProcessError) as e:
            if self.args.link_mode == "reflink":
                raise Exception(f"Reflink failed: {e}")
            elif self.args.link_mode == "hardlink":
                raise Exception(f"Hardlink failed: {e}")
            elif self.args.link_mode == "symlink":
                raise Exception(f"Symlink failed: {e}")
            else:
                raise Exception(f"Regular copy failed: {e}")

    def ingest(self, filepath):
        fpath = Path(filepath).resolve()
        try:
            file_hash = self.hasher.calculate(fpath)
        except Exception as e:
            print(f"ERR (Hash) {fpath}: {e}")
            return

        cas_path = self._get_storage_path(file_hash)
        sidecar_path = cas_path.parent / (cas_path.name + self.args.suffix)
        is_duplicate = cas_path.exists()

        if not is_duplicate:
            try:
                self._ingest_method(fpath, cas_path)
            except Exception as e:
                print(f"ERR (Copy) {fpath}: {e}")
                return

        path_id, meta = self._get_metadata(fpath)

        if sidecar_path.exists():
            data = self.sidecar_handler.load(sidecar_path)
        else:
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            data = self.sidecar_handler.create_empty(file_hash, self.args.algo)

        data["known_as"][path_id] = meta
        self.sidecar_handler.save(sidecar_path, data)

        if is_duplicate:
            print(f"DUPLICATE -> {file_hash[:8]}... ({fpath})")
            self._log_dedup_action(fpath, cas_path)
        else:
            print(f"OK -> {file_hash[:8]}... ({fpath})")

    def _log_dedup_action(self, src, dst):
        if self.args.dedup_mode == "ignore":
            return
        q_src = shlex.quote(str(src))
        q_dst = shlex.quote(str(dst))
        action_cmd = f"# Duplicate: {src}\n"
        if self.args.dedup_mode == "hardlink":
            action_cmd += f"ln -f {q_dst} {q_src}\n"
        elif self.args.dedup_mode == "softlink":
            action_cmd += f"ln -sf {q_dst} {q_src}\n"
        elif self.args.dedup_mode == "delete":
            action_cmd += f"rm {q_src}\n"
        with open(DEDUP_SCRIPT, "a") as f:
            f.write(action_cmd)

    def migrate_structure(self):
        print(f"Starting migration to shard depth: {self.args.shard_depth}")
        if self.args.shard_depth == 0:
            print("Depth 0: Moving files to root...")

        for item in self.repo.rglob("*"):
            if (
                not item.is_file()
                or item.name == CONFIG_FILE
                or item.name == DEDUP_SCRIPT
            ):
                continue

            if item.name.endswith(self.args.suffix):
                file_hash = item.name[: -len(self.args.suffix)]
            else:
                file_hash = item.name

            correct_path = self._get_storage_path(file_hash)
            if item.name.endswith(self.args.suffix):
                correct_path = correct_path.parent / (
                    correct_path.name + self.args.suffix
                )

            if item.resolve() != correct_path.resolve():
                correct_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"Moving {item.name[:8]}... -> {correct_path.parent.name}/")
                shutil.move(item, correct_path)

        for root, dirs, files in os.walk(self.repo, topdown=False):
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass
        print("Migration complete.")


def _expand_paths(paths, recursive):
    """Generator that expands paths, skipping symlinks explicitly."""
    for p_str in paths:
        p_raw = Path(p_str)

        # 1. Check if argument itself is a symlink
        if p_raw.is_symlink():
            print(f"SKIP (Symlink): {p_raw.name}")
            continue

        p = p_raw.resolve()

        if p.is_file():
            yield p
        elif p.is_dir() and recursive:
            for sub in p.rglob("*"):
                # 2. Check if recursed file is a symlink
                if sub.is_symlink():
                    # Silent skip or optional log
                    continue
                if sub.is_file():
                    yield sub
        elif p.is_dir() and not recursive:
            print(f"SKIP (Dir): {p.name} (use -r to recurse)")


# --- CLI Setup ---
args_parser = argparse.ArgumentParser(description="CAS Ingestion System")
args_parser.add_argument("repo", help="Path to CAS Repository")
args_parser.add_argument("files", nargs="*", help="Files to ingest")
args_parser.add_argument("-r", "--recursive", action="store_true", help="Recursive")
args_parser.add_argument("--algo", default="sha512", choices=["sha512", "sha256"])
args_parser.add_argument(
    "--use-external", action="store_true", help="Use external bins"
)
args_parser.add_argument("--format", default="xml", choices=["xml", "json"])
args_parser.add_argument("--suffix", default=DEFAULT_SIDECAR_SUFFIX)
args_parser.add_argument(
    "--link-mode", default="reflink", choices=["reflink", "hardlink", "symlink", "copy"]
)
args_parser.add_argument(
    "--dedup-mode",
    default="ignore",
    choices=["ignore", "delete", "hardlink", "softlink"],
)
args_parser.add_argument("--shard-depth", type=int, default=1, help="Nesting depth")
args_parser.add_argument(
    "--migrate-shards", action="store_true", help="Reorganize repo"
)

if __name__ == "__main__":
    cli_args = args_parser.parse_args()
    ingestor = CASIngestor(cli_args)

    if cli_args.dedup_mode != "ignore":
        with open(DEDUP_SCRIPT, "a") as f:
            if f.tell() == 0:
                f.write("#!/bin/bash\n")
            f.write(f"\n# Run at {datetime.now().isoformat()}\n")

    if cli_args.migrate_shards:
        ingestor.migrate_structure()

    if cli_args.files:
        for f in _expand_paths(cli_args.files, cli_args.recursive):
            ingestor.ingest(f)
