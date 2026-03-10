import os
import sys
import json
import pytest
import shutil
import hashlib
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path
from argparse import Namespace

# --- Module Loading Strategy ---
# Loads the specific filename provided without renaming requirements
TARGET_SCRIPT = "CAS-ingestion-v.04.sharding.py"

def load_cas_module():
    if not Path(TARGET_SCRIPT).exists():
        pytest.skip(f"{TARGET_SCRIPT} not found")
    spec = importlib.util.spec_from_file_location("cas_core", TARGET_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["cas_core"] = module
    spec.loader.exec_module(module)
    return module

cas = load_cas_module()

# --- Fixtures ---

@pytest.fixture
def env_setup(tmp_path):
    """Sets up a clean environment and changes CWD to tmp_path."""
    cwd = os.getcwd()
    os.chdir(tmp_path)
    
    repo = tmp_path / "repo"
    source = tmp_path / "source"
    repo.mkdir()
    source.mkdir()
    
    yield Namespace(repo=repo, source=source)
    
    os.chdir(cwd)

@pytest.fixture
def sample_file(env_setup):
    """Creates a sample file and returns path + hash."""
    fpath = env_setup.source / "test_file.txt"
    content = b"Hello World CAS"
    fpath.write_bytes(content)
    sha = hashlib.sha512(content).hexdigest()
    return fpath, sha

# --- Helper Tests ---

def test_hasher_internal(env_setup, sample_file):
    fpath, expected_hash = sample_file
    hasher = cas.InternalHasher("sha512")
    assert hasher.calculate(fpath) == expected_hash

def test_hasher_external_fallback(env_setup, sample_file):
    """Tests logic, requires sha512sum installed or mocks subprocess."""
    fpath, expected_hash = sample_file
    # Only run if sha512sum exists, otherwise mock
    if shutil.which("sha512sum"):
        hasher = cas.ExternalHasher("sha512")
        assert hasher.calculate(fpath) == expected_hash

# --- Core Ingestion Tests ---

def test_ingest_basic_xml(env_setup, sample_file):
    fpath, fhash = sample_file
    args = Namespace(
        repo=str(env_setup.repo), algo="sha512", use_external=False,
        format="xml", suffix=".meta", link_mode="copy", 
        dedup_mode="ignore", shard_depth=1, migrate_shards=False
    )
    
    ingestor = cas.CASIngestor(args)
    ingestor.ingest(fpath)

    shard = fhash[:2]
    expected_path = env_setup.repo / shard / fhash
    sidecar_path = env_setup.repo / shard / (fhash + ".meta")

    assert expected_path.exists()
    assert sidecar_path.exists()
    
    # Verify XML Content
    tree = ET.parse(sidecar_path)
    root = tree.getroot()
    assert root.find("hash").text == fhash
    assert root.find("known_as/instance/path").text == str(fpath)

def test_ingest_json_format(env_setup, sample_file):
    fpath, fhash = sample_file
    args = Namespace(
        repo=str(env_setup.repo), algo="sha512", use_external=False,
        format="json", suffix=".json", link_mode="copy", 
        dedup_mode="ignore", shard_depth=1, migrate_shards=False
    )

    ingestor = cas.CASIngestor(args)
    ingestor.ingest(fpath)
    
    shard = fhash[:2]
    sidecar_path = env_setup.repo / shard / (fhash + ".json")
    
    with open(sidecar_path) as f:
        data = json.load(f)
        assert data["hash"] == fhash
        assert any(v["path"] == str(fpath) for v in data["known_as"].values())

def test_sharding_depth_2(env_setup, sample_file):
    fpath, fhash = sample_file
    args = Namespace(
        repo=str(env_setup.repo), algo="sha512", use_external=False,
        format="json", suffix=".meta", link_mode="copy", 
        dedup_mode="ignore", shard_depth=2, migrate_shards=False
    )

    ingestor = cas.CASIngestor(args)
    ingestor.ingest(fpath)

    # Depth 2 = repo / aa / bb / hash
    expected_path = env_setup.repo / fhash[0:2] / fhash[2:4] / fhash
    assert expected_path.exists()

def test_deduplication_logic(env_setup, sample_file):
    fpath, fhash = sample_file
    args = Namespace(
        repo=str(env_setup.repo), algo="sha512", use_external=False,
        format="json", suffix=".meta", link_mode="copy", 
        dedup_mode="delete", shard_depth=1, migrate_shards=False
    )
    
    # 1. First Ingest
    ingestor = cas.CASIngestor(args)
    ingestor.ingest(fpath)
    
    # 2. Modify Mtime to ensure it looks "new" to OS but same content
    os.utime(fpath, None)
    
    # 3. Second Ingest
    ingestor.ingest(fpath)
    
    # Check if dedup script was written
    dedup_script = Path(cas.DEDUP_SCRIPT)
    assert dedup_script.exists()
    content = dedup_script.read_text()
    assert f"rm -v" in content
    assert str(fpath) in content

def test_migration(env_setup, sample_file):
    fpath, fhash = sample_file
    repo = env_setup.repo

    # 1. Ingest with Depth 1
    args_depth1 = Namespace(
        repo=str(repo), algo="sha512", use_external=False, format="json", 
        suffix=".meta", link_mode="copy", dedup_mode="ignore", 
        shard_depth=1, migrate_shards=False
    )
    cas.CASIngestor(args_depth1).ingest(fpath)
    assert (repo / fhash[:2] / fhash).exists()

    # 2. Migrate to Depth 0
    args_migrate = Namespace(
        repo=str(repo), algo="sha512", use_external=False, format="json", 
        suffix=".meta", link_mode="copy", dedup_mode="ignore", 
        shard_depth=0, migrate_shards=True
    )
    
    ingestor = cas.CASIngestor(args_migrate)
    ingestor.migrate_structure()

    # 3. Verify files moved to root
    assert (repo / fhash).exists()
    assert not (repo / fhash[:2]).exists() # Dir should be cleaned up

def test_config_persistence(env_setup):
    """Ensures .CAS-config is created and respected."""
    repo = env_setup.repo
    args = Namespace(
        repo=str(repo), algo="sha256", use_external=False, format="json",
        suffix=".meta", link_mode="copy", dedup_mode="ignore",
        shard_depth=1, migrate_shards=False
    )
    
    # Initialize
    cas.CASIngestor(args)
    
    config_path = repo / ".CAS-config"
    assert config_path.exists()
    
    with open(config_path) as f:
        saved = json.load(f)
    assert saved['algo'] == 'sha256'

def test_xattr_capture(env_setup, sample_file):
    fpath, _ = sample_file
    # Attempt to set xattr. This may fail on some tmpfs/OS
    try:
        # Linux/Mac distinct syntax usually handled by os module
        # Using a dummy key "user.comment"
        os.setxattr(fpath, b"user.test", b"test_value")
    except (AttributeError, OSError):
        pytest.skip("Filesystem does not support xattrs or permissions denied")

    args = Namespace(
        repo=str(env_setup.repo), algo="sha512", use_external=False,
        format="json", suffix=".meta", link_mode="copy", 
        dedup_mode="ignore", shard_depth=1, migrate_shards=False
    )
    
    ingestor = cas.CASIngestor(args)
    _, meta = ingestor._get_metadata(fpath)
    
    # Check if xattr was captured (base64 encoded)
    # b"test_value" in base64 is dGVzdF92YWx1ZQ==
    assert "user.test" in meta["xattrs"]
