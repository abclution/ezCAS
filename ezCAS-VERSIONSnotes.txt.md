
---------------------------------------------------------------


---------------------------------------------------------------

THESE VERSIONS ARE OBJECT ORIENTED STYLE
(MOSTLY SHARED CODEBASE)

fixd.CAS-ingestion-v.01.py
fixd.CAS-ingestion-v.02.py.problematicfileswhensplit.py
fixd.CAS-ingestion-v.03.py
fixd.CAS-ingestion-v.04.py
fixd.CAS-ingestion-v.05.py
fixd.CAS-ingestion-v.07.000.py
fixd.CAS-ingestion-v.07.001.py
fixd.CAS-ingestion-v.08.000.py

fixd.CAS-ingestion-v.08.001.py
├── CASIngestor
│   ├── _do_dedup_action.py
│   ├── _ingest_method.py
│   ├── ingest.py
│   ├── _log_dedup_action.py
│   └── _resolve_config.py

fixd.CAS-ingestion-v.08.002.py

fixd.CAS-ingestion-v.09.000.py - get_raw_xattrs function name changed to _GetFileXattrs
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

fixd.CAS-ingestion-v.09.001.py
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

fixd.alt-CAS.v.777.py
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

usage: fixd.alt-CAS.v.777.py \[-h\] \[-r\]
\[--algo {sha512,sha256}\]
\[--use-external\]
\[--format {xml,json}\]
\[--suffix SUFFIX\]
\[--link-mode {reflink,hardlink,symlink,copy}\]
\[--dedup-mode {ignore,delete,hardlink,softlink}\]
\[--shard-depth SHARD_DEPTH\]
\[--migrate-shards\]
repo \[files ...\]

CAS Ingestion System

positional arguments:
repo                  Path to CAS Repository
files                 Files to ingest

options:
\-h, --help            show this help message and exit
\-r, --recursive       Recursive
\--algo {sha512,sha256}
\--use-external        Use external bins
\--format {xml,json}
\--suffix SUFFIX
\--link-mode {reflink,hardlink,symlink,copy}
\--dedup-mode {ignore,delete,hardlink,softlink}
\--shard-depth SHARD_DEPTH
Nesting depth
\--migrate-shards      Reorganize repo


---------------------------------------------------------------


---------------------------------------------------------------


---------------------------------------------------------------


---------------------------------------------------------------

PURELY FUNCTIONAL BASED STYLE
(MOSTLY SHARED CODEBASE)

fixd.CAS-addfiles-v.01.000.py
fixd.CAS-addfiles-v.01.001.py - timestamping for log added here
fixd.CAS-addfiles-v.02.000.py
fixd.CAS-addfiles-v.02.001.py
fixd.CAS-addfiles-v.03.py   - replaced ingest with "process"

fixd.ez-CAS.v.01.py - almost identical to fixd.CAS-addfiles-v.03.py

usage: fixd.ez-CAS.v.01.py \[-h\] \[-r\] \[-f\]

options:
\-h, --help            show this help message and exit
\-r, --recursive
\-f, --force
\--algo {sha512,sha256}
\--use-external
\--format {xml,json}
\--suffix SUFFIX
\--ingest-method
{
copy,
hardlink,
ignore,
move,
reflink,
symlink}

\--dedupe-action
{delete,hardlink,ignore,reflink,symlink}
\--shard-depth SHARD_DEPTH
\--migrate-shards

positional arguments:
repo
files


---------------------------------------------------------------


---------------------------------------------------------------


---------------------------------------------------------------


---------------------------------------------------------------

PURELY FUNCTIONAL BASED STYLE
(UNIQUE CODEBASE)

fixd_ingestion_manager.py

FUNCTION LIST
get_file_hash.py
get_raw_xattrs.py
get_xattrs.py
ingest_file.py
main.py
reflink_copy.py
restore_xattrs.py
update_sidecar.py

```
usage: fixd_ingestion_manager.py options
```

Fixd Ingestion Manager

options:
\-h, --help            show this help message and exit
\--cas-root CAS_ROOT   Root directory for CAS storage (default: cas_store)
\--algo  (default: sha256)
{md5-sha1,md5,sha512_256,
blake2b,sha512,sha3_512,shake_256,
sha1,sha3_224,sha384,sha3_256,sm3,
sha256,shake_128,sha224,sha3_384,
sha512_224,blake2s,ripemd160}   Hashing algorithm to use

\--dedup-source        Overwrite source duplicate with reflink from CAS (Deduplicate in-place).
\--delete-dup          Delete source file if it exists in CAS.
\--mark-dup SUFFIX     Rename duplicate source files with suffix (e.g., .DELETED).
\--move-dup DIR        Move duplicate source files to specified directory.

positional arguments:
path                  File or Directory to input


---------------------------------------------------------------


---------------------------------------------------------------


---------------------------------------------------------------


---------------------------------------------------------------

PURELY FUNCTIONAL BASED STYLE
(UNIQUE CODEBASE)

# gemini-code-1785602175544.py

## FUNCTION LIST

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

usage: gemini-code-1785602175544.py
\[--algo {sha256,sha512}\]
\[--dedup-mode {ignore,delete,hardlink,softlink}\]
\[--format {xml,json}\]
\[--link-mode {reflink,hardlink,symlink,copy,move}\]
\[--migrate-shards\]
\[--shard-depth SHARD_DEPTH\]
\[--suffix SUFFIX\]
\[-h\]
\[-r\]
repo \[files ...\]

ezCAS Storage Utility

positional arguments:
repo                  Path to CAS Repository
files                 Files to ingest

options:
\--algo {sha256,sha512}
\--dedup-mode {ignore,delete,hardlink,softlink}
\--format {xml,json}
\--link-mode {reflink,hardlink,symlink,copy,move}
\--migrate-shards
\--shard-depth SHARD_DEPTH
\--suffix SUFFIX
\-h, --help            show this help message and exit
\-r, --recursive       Recursive ingestion

gemini-code-1785602175544.py -r --dedup-mode delete /zpool_8tb-ext/ezCAS-TESTING/CAS-datastore-04 /zpool_8tb-ext/ezCAS-TESTING/in-04

gemini-code-1785602175544.py --migrate-shards --shard-depth 1 /zpool_8tb-ext/ezCAS-TESTING/CAS-datastore-04






| <u>CHECKS</u>                                     | RESULT | NOTES |
| :------------------------------------------------ | ------ | ----- |
| Config file created?                              |        |       |
| Secondary run w/o switches follows config?        |        |       |
| Major switch changes throw error? Which switches? |        |       |
| Shard depth obeyed?                               |        |       |
| Shard depth reorg ok?                             |        |       |
| Sidecar created ok? XML? JSON?                    |        |       |
| Skip zero size files                              |        |       |
| Skip symlinks                                     |        |       |
|                                                   |        |       |
|                                                   |        |       |

\--- Configuration & Constants ---



TODO: ADD / TEST SOME CHECKS WHEN INGESTING AND VALIDATING DUPLICATES WHEN IN CAS ITEM IS SYMLINK. EITHER REFUSE TO REMOVE DUPLICATE THAT POINTS TO SYMLINKIN CAS, OR RESOLVE SYMLINK INTO A FILE/HARDLINK FIRST, THEN DEDUPE.



TESTED: DEDUPE/INGEST SYMLINK/SYMLINK FAILS IF NEW, TESTED: ADD VIA HARDLINK OR ALREADY IN CAS, copy as reflink fails due tofile existing. force does not work either. Must rm file first bug? not sure

TSiso={datetime.now().isoformat()}

CHECKS

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


---------------------------------------------------------------


---------------------------------------------------------------


