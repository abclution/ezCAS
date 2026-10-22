# ezCAS Development Notes

## NOTES

### Example commands for testing

```

fixd.CAS-ingestion-v.02.sharding.py \
    --migrate-shards \
    --shard-depth 2  \
    -r --algo sha512 \
    --format xml \
    --link-mode reflink \
    --dedup-mode ignore \
    ./CAS-STORAGE ./INCOMING FILES

gemini-code-1785602175544.py \
    -r \
    --dedup-mode delete \
    /zpool_8tb-ext/ezCAS-TESTING/CAS-datastore-04 /zpool_8tb-ext/ezCAS-TESTING/in-04

gemini-code-1785602175544.py \
    --migrate-shards \
    --shard-depth 1 \
    /zpool_8tb-ext/ezCAS-TESTING/CAS-datastore-04
```

# TODOS

* ADD / TEST SOME CHECKS WHEN INGESTING AND VALIDATING DUPLICATES WHEN IN CAS ITEM IS SYMLINK.
  * EITHER REFUSE TO REMOVE DUPLICATE THAT POINTS TO SYMLINKIN CAS, OR RESOLVE SYMLINK INTO A FILE/HARDLINK FIRST, THEN DEDUPE.
  * DEDUPE/INGEST SYMLINK/SYMLINK FAILS IF NEW, TESTED: ADD VIA HARDLINK OR ALREADY IN CAS, copy as reflink fails due tofile existing. force does not work either.
  * Must rm file first bug? not sure


---

# AI ASSIST NOTES


---

| QUESTION |
|----|
| Please create a docstring description for this python function as well as add an option to use the local filesystem utility "getfattr" the -d switch and output using -e switch in all three formats text, hex, base64 |

```
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
```


---





| QUESTION |
|----|
| Please modify the following function to use the built in getfattr system binary (and make it the default) getfattr should be called with the switches -d (output all extended attribute values) & -e text/hex/base64 (encode output values (as 'text', 'hex' or 'base64') based on the function parameter encoding. Adjust the python library function to match accordingly when called. Please create a docstring description for this python function afterwards. Thanks. |

```
def extract_xattrs(filepath,encoding=text):
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
```


---

| QUESTION |
|----|
| Ok, some first corrections. Logs while properly separated, should be timestamped per session, not per file, so ts (timestamp prefix) should be consistent across each log per session.  Progress during the session should be visible by default, including what attributes, standard + extended are found & saved,  perhaps a -q / --quiet switch to reduce output other than errors. |



# TESTS & TESTING TABLE

## CHECKS

* Config file created?
  * Secondary run w/o switches follows config?
  * Major switch changes throw error? Which switches?
* Shard depth obeyed?
  * Shard depth reorg ok?
* Sidecar created ok?
  * XML?
  * JSON?
* Skip zero size files
* \



| *<u>CHECKS</u>* | *<u>RESULT</u>* | *<u>NOTES</u>* |
|:---|----|----|
| Config file created? |    |    |
| - Secondary run w/o switches follows config? |    |    |
| - Major switch changes throw config error? |    |    |
| - Which switches? |    |    |
| Shard depth obeyed? |    |    |
| Shard depth reorg ok? |    |    |
| Sidecar created ok? XML? JSON? |    |    |
| Skip zero size files |    |    |
| Skip symlinks |    |    |
|    |    |    |
|    |    |    |


---

### Misc

```
31.5 GiB (33,770,216,304)
38,448 files, 804 sub-folders

11.6 GiB (12,503,163,096)
38,211 files, 804 sub-folders

cd /zpool_20tb/eVAULT/GALLERY/GALLERY_Staging_Folders

276.3 GiB (296,635,773,348)
76,326 files, 8,598 sub-folders

260.6 GiB (279,855,608,112)
51,125 files, 8,598 sub-folders
```

\###################################################################################


## HELPER FUNCTIONS NOTES

### SPLITMODULE NOTES

```
find ./  -iname '*.py'   ! -type l  -exec md5sum {}  \; |sort -t. -k2
46964cfa1b23a4f2d17f75b0b61709fd  ./fixd.alt-CAS.v.777/CASIngestor/_get_hasher.py
2135bc63400a3bcb590f9c4dc48ce725  ./fixd.alt-CAS.v.777/CASIngestor/_get_metadata.py
30dc8cad8bc068804aa6ae00cc885fd3  ./fixd.alt-CAS.v.777/CASIngestor/_get_storage_path.py
...
```


./fixd.CAS-ingestion-v.04/_expand_paths.py






---

# OBJECT ORIENTED STYLE VERSIONS

> THESE VERSIONS ARE OBJECT ORIENTED STYLE
> (MOSTLY SHARED CODEBASE)

* fixd.CAS-ingestion-v.01.py
* fixd.CAS-ingestion-v.02.py
  * Problem when seperating functions however fix was easy.
* fixd.CAS-ingestion-v.03.py
* fixd.CAS-ingestion-v.04.py
* fixd.CAS-ingestion-v.05.py
* fixd.CAS-ingestion-v.07.000.py
* fixd.CAS-ingestion-v.07.001.py
* fixd.CAS-ingestion-v.08.000.py


---


---

## fixd.CAS-ingestion-v.08.001.py

### FUNCTIONS

```
├── CASIngestor
│   ├── _do_dedup_action.py
│   ├── _ingest_method.py
│   ├── ingest.py
│   ├── _log_dedup_action.py
│   └── _resolve_config.py
```


---

## fixd.CAS-ingestion-v.08.002.py

### FUNCTIONS


---

## fixd.CAS-ingestion-v.09.000.py

### FUNCTIONS

```
Notable changes from previous version
get_raw_xattrs function name changed to _GetFileXattrs

├── CASIngestor
│   ├── _DoDedupeAction.py
│   ├── _GetMetadata.py
│   ├── _GetStoragePath.py
│   ├── _IngestMethod.py
│   ├── ingest.py
│   ├── _LogDedupeAction.py
│   ├── migrate_structure.py
│   └── _resolve_config.py -> ../../fixd.CAS-ingestion-v.08.001/CASIngestor/_resolve_config.py
├── _GetFileXattrs.py
```


---

## fixd.CAS-ingestion-v.09.001.py

### FUNCTIONS: fixd.CAS-ingestion-v.09.001.py

```
├── CASIngestor
│   ├── _DoDedupeAction.py -> ../../fixd.CAS-ingestion-v.09.000/CASIngestor/_DoDedupeAction.py
│   ├── _GetMetadata.py -> ../../fixd.CAS-ingestion-v.09.000/CASIngestor/_GetMetadata.py
│   ├── _GetStoragePath.py -> ../../fixd.CAS-ingestion-v.09.000/CASIngestor/_GetStoragePath.py
│   ├── _IngestHardlink.py
│   ├── _IngestMethod.py
│   ├── _IngestMove.py
│   ├── ingest.py -> ../../fixd.CAS-ingestion-v.09.000/CASIngestor/ingest.py
│   ├── _IngestReflink.py
│   ├── _IngestSoftlink.py
│   ├── _LogDedupeAction.py -> ../../fixd.CAS-ingestion-v.09.000/CASIngestor/_LogDedupeAction.py
│   ├── migrate_structure.py -> ../../fixd.CAS-ingestion-v.09.000/CASIngestor/migrate_structure.py
│   └── _resolve_config.py -> ../../fixd.CAS-ingestion-v.08.001/CASIngestor/_resolve_config.py
├── _GetFileXattrs.py -> ../fixd.CAS-ingestion-v.09.000/_GetFileXattrs.py
```


---

## fixd.alt-CAS.v.777.py

### FUNCTIONS: fixd.alt-CAS.v.777.py

```
├── CASIngestor
│   ├── _get_hasher.py
│   ├── _get_metadata.py
│   ├── _get_storage_path.py
│   ├── _ingest_method.py
│   ├── ingest.py
│   ├── __init__.py
│   ├── _log_dedup_action.py
│   ├── migrate_structure.py
│   └── _resolve_config.py
├── _expand_paths.py
├── ExternalHasher
│   ├── calculate.py
│   └── __init__.py
├── get_raw_xattrs.py
├── Hasher
│   └── calculate.py
├── InternalHasher
│   ├── calculate.py
│   └── __init__.py
├── JSONHandler
│   ├── create_empty.py
│   ├── load.py
│   └── save.py
├── SidecarHandler
│   ├── create_empty.py
│   ├── load.py
│   └── save.py
└── XMLHandler
├── create_empty.py -> ../JSONHandler/create_empty.py
├── load.py
└── save.py
```

## USAGE: fixd.alt-CAS.v.777.py

```
fixd.alt-CAS.v.777.py

CAS Ingestion System

options:
-h, --help              show this help message and exit
-r, --recursive         Recursive
--algo                  {sha512,sha256}
--use-external          Use external bins
--format                {xml,json}
--suffix                SUFFIX
--link-mode             {reflink,hardlink,symlink,copy}
--dedup-mode            {ignore,delete,hardlink,softlink}
--shard-depth           SHARD_DEPTH Nesting depth
--migrate-shards        Reorganize repo
repo [files ...]

positional arguments:
repo                  Path to CAS Repository
files                 Files to ingest
```


---


---

# FUNCTIONAL PROGRAMMING BASED VERSIONS

> (MOSTLY SHARED CODEBASE)

* fixd.CAS-addfiles-v.01.000.py
* fixd.CAS-addfiles-v.01.001.py
  * timestamping for log added here
* fixd.CAS-addfiles-v.02.000.py
* fixd.CAS-addfiles-v.02.001.py
* fixd.CAS-addfiles-v.03.py
  * replaced ingest with "process"
* fixd.ez-CAS.v.01.py
  * Continoution of CAS-addfiles versions.
  * Almost identical to fixd.CAS-addfiles-v.03.py


---

### fixd.ez-CAS.v.01.py

```
usage: fixd.ez-CAS.v.01.py [-h] [-r] [-f]

options:
-h, --help            show this help message and exit
-r, --recursive
-f, --force
--algo {sha512,sha256}
--use-external
--format {xml,json}
--suffix SUFFIX
--ingest-method
{
copy,
hardlink,
ignore,
move,
reflink,
symlink}

--dedupe-action
{delete,hardlink,ignore,reflink,symlink}
--shard-depth SHARD_DEPTH
--migrate-shards

positional arguments:
repo
files
```


---


---

## fixd_ingestion_manager.py

> PURELY FUNCTIONAL BASED STYLE (UNIQUE CODEBASE)

### FUNCTION LIST

```
get_file_hash.py
get_raw_xattrs.py
get_xattrs.py
ingest_file.py
main.py
reflink_copy.py
restore_xattrs.py
update_sidecar.py
```

### USAGE

```
usage: fixd_ingestion_manager.py options
Fixd Ingestion Manager

options:
-h, --help            show this help message and exit
--cas-root CAS_ROOT   Root directory for CAS storage (default: cas_store)
--algo  (default: sha256)
{md5-sha1,md5,sha512_256,
blake2b,sha512,sha3_512,shake_256,
sha1,sha3_224,sha384,sha3_256,sm3,
sha256,shake_128,sha224,sha3_384,
sha512_224,blake2s,ripemd160}   Hashing algorithm to use

--dedup-source        Overwrite source duplicate with reflink from CAS (Deduplicate in-place).
--delete-dup          Delete source file if it exists in CAS.
--mark-dup SUFFIX     Rename duplicate source files with suffix (e.g., .DELETED).
--move-dup DIR        Move duplicate source files to specified directory.

positional arguments:
path                  File or Directory to input
```


---

## gemini-code-1785602175544.py

> PURELY FUNCTIONAL BASED STYLE (UNIQUE CODEBASE)

### FUNCTION LIST

```
atomic_write.py
calculate_hash.py
extract_metadata.py
extract_xattrs.py
get_shard_dir.py
get_timestamp_prefix.py
handle_dedup.py
ingest_file.py
load_or_init_config.py
log_and_script.py
main.py
migrate_shards.py
perform_link.py
read_sidecar.py
set_immutability.py
write_sidecar.py
```

### USAGE

```
ezCAS Storage Utility 
usage: gemini-code-1785602175544.py

options:
--algo {sha256,sha512}
--dedup-mode {ignore,delete,hardlink,softlink}
--format {xml,json}
--link-mode {reflink,hardlink,symlink,copy,move}
--migrate-shards
--shard-depth SHARD_DEPTH
--suffix SUFFIX
-h, --help            show this help message and exit
-r, --recursive       Recursive ingestion
repo [files ...]

positional arguments:
repo                  Path to CAS Repository
files                 Files to ingest
```


---


