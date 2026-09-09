#!/usr/bin/env bash
set -eo pipefail

CONFIG_FILE=".CAS-config"
DEFAULT_SIDECAR_SUFFIX=".known-as"
DEDUP_SCRIPT="CAS-dedupActionlist.sh"

REPO=""
FILES=()
RECURSIVE=1
FORCE=0
ALGO="sha512"
FORMAT="xml"
SUFFIX="$DEFAULT_SIDECAR_SUFFIX"
INGEST_METHOD="hardlink"
DEDUPE_ACTION="ignore"
SHARD_DEPTH=2
MIGRATE_SHARDS=0

parse_args() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
		-r | --recursive)
			RECURSIVE=1
			shift
			;;
		-f | --force)
			FORCE=1
			shift
			;;
		--algo)
			ALGO="$2"
			shift 2
			;;
		--format)
			FORMAT="$2"
			shift 2
			;;
		--suffix)
			SUFFIX="$2"
			shift 2
			;;
		--ingest-method)
			INGEST_METHOD="$2"
			shift 2
			;;
		--dedupe-action)
			DEDUPE_ACTION="$2"
			shift 2
			;;
		--shard-depth)
			SHARD_DEPTH="$2"
			shift 2
			;;
		--migrate-shards)
			MIGRATE_SHARDS=1
			shift
			;;
		-*)
			printf "Unknown option %s\n" "$1"
			exit 1
			;;
		*)
			if [[ -z "$REPO" ]]; then
				REPO=$(realpath "$1")
			else
				FILES+=("$1")
			fi
			shift
			;;
		esac
	done
}

load_config() {
	local cfg_path="$REPO/$CONFIG_FILE"
	if [[ -f "$cfg_path" ]] && command -v jq &>/dev/null; then
		ALGO=$(jq -r '.algo // "sha512"' "$cfg_path")
		FORMAT=$(jq -r '.format // "xml"' "$cfg_path")
		INGEST_METHOD=$(jq -r '.ingest_method // "hardlink"' "$cfg_path")
		DEDUPE_ACTION=$(jq -r '.dedupe_action // "ignore"' "$cfg_path")
		SHARD_DEPTH=$(jq -r '.shard_depth // 2' "$cfg_path")
	fi
}

save_config() {
	local cfg_path="$REPO/$CONFIG_FILE"
	if command -v jq &>/dev/null; then
		jq -n \
			--arg algo "$ALGO" \
			--arg format "$FORMAT" \
			--arg method "$INGEST_METHOD" \
			--arg dedup "$DEDUPE_ACTION" \
			--arg depth "$SHARD_DEPTH" \
			'{
                algo: $algo, 
                format: $format, 
                ingest_method: $method, 
                dedupe_action: $dedup, 
                shard_depth: ($depth|tonumber)
            }' >"$cfg_path"
	fi
}

calculate_hash() {
	local filepath="$1"
	if [[ "$ALGO" == "sha256" ]]; then
		sha256sum "$filepath" | awk '{print $1}'
	else
		sha512sum "$filepath" | awk '{print $1}'
	fi
}

get_storage_path() {
	local hash="$1"
	if ((SHARD_DEPTH == 0)); then
		echo "$REPO/$hash"
		return
	fi
	local path="$REPO"
	for ((i = 0; i < SHARD_DEPTH; i++)); do
		local start=$((i * 2))
		path="$path/${hash:start:2}"
	done
	echo "$path/$hash"
}

get_metadata() {
	local filepath="$1"
	local path_id stat_size stat_mtime stat_mode
	path_id=$(echo -n "$filepath" | sha256sum | awk '{print $1}')
	stat_size=$(stat -c %s "$filepath")
	stat_mtime=$(stat -c %Y "$filepath")
	stat_mode=$(stat -c %a "$filepath")

	printf "%s|%s|%s|%s|%s" \
		"$path_id" \
		"$(date -Iseconds)" \
		"$stat_size" \
		"$stat_mtime" \
		"$stat_mode"
}

ingest_method_exec() {
	local src="$1"
	local dst="$2"

	mkdir -p "$(dirname "$dst")"

	case "$INGEST_METHOD" in
	reflink) cp --preserve=all --reflink=always "$src" "$dst" ;;
	move)
		if [[ "$DEDUPE_ACTION" =~ ^(ignore|delete)$ ]] && ((FORCE == 0)); then
			printf "Move + %s isolates CAS. Use -f/--force.\n" "$DEDUPE_ACTION"
			exit 1
		fi
		mv -vn "$src" "$dst"
		do_dedupe_action "$src" "$dst"
		;;
	hardlink) ln "$src" "$dst" ;;
	symlink) ln -s "$src" "$dst" ;;
	*) exit 1 ;;
	esac
}

do_dedupe_action() {
	local origin="$1"
	local incas="$2"

	case "$DEDUPE_ACTION" in
	ignore) return ;;
	hardlink)
		ln -vf "$incas" "$origin"
		printf "HARDLINKING -> \n%s\n to \n%s\n" "$incas" "$origin"
		;;
	symlink)
		ln -vsf "$incas" "$origin"
		printf "SYMLINKING -> \n%s\n to \n%s\n" "$incas" "$origin"
		;;
	reflink)
		cp -v --preserve=all --reflink=always "$incas" "$origin"
		printf "COPYING (REFLINK) -> \n%s\n to \n%s\n" "$incas" "$origin"
		;;
	delete)
		rm "$origin"
		printf "DELETING -> \n%s\n" "$origin"
		;;
	esac
}

log_dedupe_action() {
	local src="$1"
	local dst="$2"
	local q_src q_dst action_cmd

	if [[ "$DEDUPE_ACTION" == "ignore" ]]; then return; fi

	q_src=$(printf '%q' "$src")
	q_dst=$(printf '%q' "$dst")
	action_cmd="# Duplicate: $src\n"

	case "$DEDUPE_ACTION" in
	hardlink) action_cmd+="ln -vf $q_dst $q_src\n" ;;
	symlink) action_cmd+="ln -vsf $q_dst $q_src\n" ;;
	reflink) action_cmd+="cp -v --preserve=all --reflink=always $q_src $q_dst\n" ;;
	delete) action_cmd+="rm -fv $q_src\n" ;;
	esac

	if ((FORCE == 1)); then
		action_cmd+="# Force switch enabled, $DEDUPE_ACTION processed.\n"
		do_dedupe_action "$src" "$dst"
	fi

	printf "%b" "$action_cmd" >>"$DEDUP_SCRIPT"
}

migrate_structure() {
	printf "Starting migration to shard depth: %d\n" "$SHARD_DEPTH"

	while IFS= read -r -d '' item; do
		local filename
		filename=$(basename "$item")

		if [[ "$filename" == "$CONFIG_FILE" || "$filename" == "$DEDUP_SCRIPT" ]]; then
			continue
		fi

		local file_hash="$filename"
		if [[ "$filename" == *"$SUFFIX" ]]; then
			file_hash="${filename%$SUFFIX}"
		fi

		local correct_path
		correct_path=$(get_storage_path "$file_hash")

		if [[ "$filename" == *"$SUFFIX" ]]; then
			correct_path="$(dirname "$correct_path")/${filename}"
		fi

		if [[ "$(realpath "$item")" != "$(realpath -m "$correct_path")" ]]; then
			mkdir -p "$(dirname "$correct_path")"
			printf "Moving %s... -> %s/\n" "${filename:0:8}" "$(basename "$(dirname "$correct_path")")"
			mv "$item" "$correct_path"
		fi
	done < <(find "$REPO" -type f -print0)

	find "$REPO" -type d -empty -delete
	printf "Migration complete.\n"
}

file_into_cas() {
	local fpath
	fpath=$(realpath "$1")

	local file_hash
	if ! file_hash=$(calculate_hash "$fpath"); then
		printf "ERR (Hash) %s\n" "$fpath"
		return
	fi

	local cas_path sidecar_path is_duplicate
	cas_path=$(get_storage_path "$file_hash")
	sidecar_path="$(dirname "$cas_path")/$(basename "$cas_path")$SUFFIX"

	is_duplicate=0
	[[ -e "$cas_path" ]] && is_duplicate=1

	if ((is_duplicate == 0)); then
		if ! ingest_method_exec "$fpath" "$cas_path"; then
			printf "ERR (Copy) %s\n" "$fpath"
			return
		fi
	fi

	if ((is_duplicate == 1)); then
		printf "DUPLICATE -> %s... (%s)\n" "${file_hash:0:8}" "$fpath"
		log_dedupe_action "$fpath" "$cas_path"
		if ((FORCE == 1)); then
			do_dedupe_action "$fpath" "$cas_path"
		fi
	else
		printf "OK -> %s... (%s)\n" "${file_hash:0:8}" "$fpath"
	fi
}

expand_paths() {
	for p_str in "${FILES[@]}"; do
		if [[ -L "$p_str" ]]; then
			printf "SKIP (Symlink): %s\n" "$(basename "$p_str")"
			continue
		fi

		local p
		p=$(realpath "$p_str")

		if [[ -f "$p" ]]; then
			file_into_cas "$p"
		elif [[ -d "$p" && "$RECURSIVE" -eq 1 ]]; then
			while IFS= read -r -d '' sub; do
				if [[ ! -L "$sub" ]]; then
					file_into_cas "$sub"
				fi
			done < <(find "$p" -type f -print0)
		elif [[ -d "$p" && "$RECURSIVE" -eq 0 ]]; then
			printf "SKIP (Dir): %s (use -r to recurse)\n" "$(basename "$p")"
		fi
	done
}

main() {
	parse_args "$@"

	if [[ -z "$REPO" ]]; then
		printf "Usage: %s REPO [FILES...]\n" "$0"
		exit 1
	fi

	mkdir -p "$REPO"
	load_config
	save_config

	if [[ ! -f "$DEDUP_SCRIPT" ]]; then
		printf "#!/bin/bash\n" >"$DEDUP_SCRIPT"
	fi
	printf "\n# Run at %s\n# Options: %s\n" "$(date -Iseconds)" "$*" >>"$DEDUP_SCRIPT"

	if ((MIGRATE_SHARDS == 1)); then
		migrate_structure
	fi

	if [[ ${#FILES[@]} -gt 0 ]]; then
		expand_paths
	fi
}

main "$@"
