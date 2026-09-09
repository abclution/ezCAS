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
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# --- Configuration & Constants ---
CONFIG_FILE = ".CAS-config"
DEFAULT_SIDECAR_SUFFIX = ".known-as"
DEDUP_SCRIPT = "fixd_dedup_actions.sh"


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
            meta = {child.tag: child.text for child in inst}
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
                    continue
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
        if not config_path.exists():
            with open(config_path, "w") as f:
                opts = {
                    k: v
                    for k, v in vars(args).items()
                    if k in ["algo", "use_external", "format", "link_mode"]
                }
                json.dump(opts, f)
        elif saved_opts:
            for k, v in saved_opts.items():
                if getattr(args, k) == getattr(args_parser.get_default(k), k, None):
                    setattr(final_ns, k, v)
        return final_ns

    def _get_hasher(self):
        algo = self.args.algo
        if self.args.use_external:
            return ExternalHasher(algo)
        return InternalHasher(algo)

    def _get_metadata(self, filepath):
        stat = os.stat(filepath)
        path_hash = hashlib.sha256(str(filepath.resolve()).encode()).hexdigest()
        meta = {
            "path": str(filepath.resolve()),
            "ingested_at": datetime.now().isoformat(),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "mode": oct(stat.st_mode)[-3:],
            "xattrs": "TODO",
        }
        return path_hash, meta

    def _reflink_copy(self, src, dst):
        if dst.exists():
            return
        try:
            if platform.system() == "Darwin":
                os.clonefile(src, dst)
            else:
                subprocess.run(
                    ["cp", "--reflink=always", src, dst],
                    check=True,
                    capture_output=True,
                )
        except (OSError, subprocess.CalledProcessError) as e:
            if self.args.link_mode == "reflink":
                raise Exception(f"Reflink failed: {e}")
            elif self.args.link_mode == "hardlink":
                os.link(src, dst)
            elif self.args.link_mode == "symlink":
                os.symlink(src, dst)
            else:
                shutil.copy2(src, dst)

    def ingest(self, filepath):
        fpath = Path(filepath).resolve()

        try:
            file_hash = self.hasher.calculate(fpath)
        except Exception as e:
            print(f"ERR (Hash) {fpath.name}: {e}")
            return

        cas_path = self.repo / file_hash
        sidecar_path = self.repo / (file_hash + self.args.suffix)
        is_duplicate = cas_path.exists()

        if not is_duplicate:
            try:
                self._reflink_copy(fpath, cas_path)
            except Exception as e:
                print(f"ERR (Copy) {fpath.name}: {e}")
                return

        path_id, metadata = self._get_metadata(fpath)
        if sidecar_path.exists():
            data = self.sidecar_handler.load(sidecar_path)
        else:
            data = self.sidecar_handler.create_empty(file_hash, self.args.algo)

        data["known_as"][path_id] = metadata
        self.sidecar_handler.save(sidecar_path, data)

        if is_duplicate:
            print(f"DUPLICATE -> {file_hash[:8]}... ({fpath.name})")
            self._log_dedup_action(fpath, cas_path)
        else:
            print(f"OK -> {file_hash[:8]}... ({fpath.name})")

    def _log_dedup_action(self, src, dst):
        if self.args.dedup_mode == "ignore":
            return

        # Use shlex.quote to safely escape filenames for shell execution
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


def _expand_paths(paths, recursive):
    for p_str in paths:
        p = Path(p_str).resolve()
        if p.is_file():
            yield p
        elif p.is_dir():
            if recursive:
                for sub in p.rglob("*"):
                    if sub.is_file():
                        yield sub
            else:
                print(f"SKIP (Dir): {p.name} (use -r to recurse)")


# --- CLI Setup ---
args_parser = argparse.ArgumentParser(description="CAS Ingestion System")
args_parser.add_argument("repo", help="Path to CAS Repository")
args_parser.add_argument("files", nargs="+", help="Files or Directories to ingest")
args_parser.add_argument(
    "-r", "--recursive", action="store_true", help="Recursively process directories"
)
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

if __name__ == "__main__":
    cli_args = args_parser.parse_args()
    ingestor = CASIngestor(cli_args)

    if cli_args.dedup_mode != "ignore":
        # Create script if missing, verify writable
        with open(DEDUP_SCRIPT, "a") as f:
            f.write(f"\n# Run at {datetime.now().isoformat()}\n")
            # Add shebang only if empty/new
            if f.tell() == 0:
                f.write("#!/bin/bash\n")

    for f in _expand_paths(cli_args.files, cli_args.recursive):
        ingestor.ingest(f)
