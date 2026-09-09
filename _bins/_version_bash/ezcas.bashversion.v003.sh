#!/usr/bin/env bash
#set -euo pipefail
set -eo pipefail

CONFIG_FILE=".CAS-config"
DEFAULT_SIDECAR_SUFFIX=".known-as"
DEDUP_SCRIPT_NAME="CAS-dedupActionlist.sh"

REPO=""
FILES=()

RECURSIVE=0
FORCE=0

ALGO="sha512"
FORMAT="xml"
SUFFIX="$DEFAULT_SIDECAR_SUFFIX"
INGEST_METHOD="hardlink"
DEDUPE_ACTION="ignore"
SHARD_DEPTH=2
MIGRATE_SHARDS=0

CLI_ALGO=0
CLI_FORMAT=0
CLI_INGEST=0
CLI_DEDUPE=0
CLI_SHARDS=0

sTIMER=".2"
#DEBUG="True"
DEBUG="False"

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEEBUG() {
	#* EZ DEBUG FUNCTION, TAKES UP TO 8 ARGS THAT ARE EVALUATED AND SLEEPS AT THE END OF EACH CALL
	#! USAGE: DEEBUG 'echo -e "\nEXAMPLE DEBUG NOTIFICATION \n"''

	if [[ "$DEBUG" == "True" ]]; then

		# local dbugCMD01="$1"
		local dbugCMD02="$2"
		local dbugCMD03="$3"
		local dbugCMD04="$4"
		local dbugCMD05="$5"
		local dbugCMD06="$6"
		local dbugCMD07="$7"
		local dbugCMD08="$8"
		echo -e "\n# ━━ DEBUG ━━━ [ $1 ] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
		# echo -e "\n $1 $2 $3 $4 \n"
		#eval "$dbugCMD01"
		eval "$dbugCMD02"
		eval "$dbugCMD03"
		eval "$dbugCMD04"
		eval "$dbugCMD05"
		eval "$dbugCMD06"
		eval "$dbugCMD07"
		eval "$dbugCMD08"

		#echo -e "\n# ━━ DEBUG END ━━━━━ [ $1 ] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

		if [[ "$sTIMER" == "wait" ]]; then
			echo -e "\n"
			read -r -p "Enter to continue..."
		else
			echo -e "\nContinuing in ${sTIMER} seconds.."
			sleep ${sTIMER}
		fi

	fi
}
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

resolve_path() {
	DEEBUG "${FUNCNAME[0]}"
	realpath "$1" 2>/dev/null || readlink -f "$1"
}

parse_args() {
	DEEBUG "${FUNCNAME[0]}"
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
			CLI_ALGO=1
			shift 2
			;;
		--format)
			FORMAT="$2"
			CLI_FORMAT=1
			shift 2
			;;
		--ingest-method)
			INGEST_METHOD="$2"
			CLI_INGEST=1
			shift 2
			;;
		--dedupe-action)
			DEDUPE_ACTION="$2"
			CLI_DEDUPE=1
			shift 2
			;;
		--shard-depth)
			SHARD_DEPTH="$2"
			CLI_SHARDS=1
			shift 2
			;;
		--suffix)
			SUFFIX="$2"
			shift 2
			;;
		--migrate-shards)
			MIGRATE_SHARDS=1
			shift
			;;
		-*)
			printf 'Unknown option: %s\n' "$1"
			exit 1
			;;
		*)
			if [[ -z "$REPO" ]]; then
				REPO=$(resolve_path "$1")
			else
				FILES+=("$1")
			fi
			shift
			;;
		esac
	done
}

load_config() {
	DEEBUG "${FUNCNAME[0]}"

	local cfg="$REPO/$CONFIG_FILE"
	[[ -f "$cfg" ]] || return 0
	command -v jq >/dev/null 2>&1 || return 0

	[[ $CLI_ALGO -eq 0 ]] && ALGO=$(jq -r '.algo // "sha512"' "$cfg")
	[[ $CLI_FORMAT -eq 0 ]] && FORMAT=$(jq -r '.format // "xml"' "$cfg")
	[[ $CLI_INGEST -eq 0 ]] && INGEST_METHOD=$(jq -r '.ingest_method // "hardlink"' "$cfg")
	[[ $CLI_DEDUPE -eq 0 ]] && DEDUPE_ACTION=$(jq -r '.dedupe_action // "ignore"' "$cfg")
	[[ $CLI_SHARDS -eq 0 ]] && SHARD_DEPTH=$(jq -r '.shard_depth // 2' "$cfg")
}

save_config() {
	DEEBUG "${FUNCNAME[0]}"

	command -v jq >/dev/null 2>&1 || return 0
	jq -n \
		--arg algo "$ALGO" \
		--arg format "$FORMAT" \
		--arg method "$INGEST_METHOD" \
		--arg dedupe "$DEDUPE_ACTION" \
		--arg depth "$SHARD_DEPTH" \
		'{algo:$algo,format:$format,ingest_method:$method,dedupe_action:$dedupe,shard_depth:($depth|tonumber)}' \
		>"$REPO/$CONFIG_FILE"
}

calculate_hash() {
	DEEBUG "${FUNCNAME[0]}"
	if [[ "$ALGO" == "sha256" ]]; then
		sha256sum "$1" | awk '{print $1}'
	else
		sha512sum "$1" | awk '{print $1}'
	fi
}

get_storage_path() {
	DEEBUG "${FUNCNAME[0]}"
	local hash="$1"
	local path="$REPO"

	if ((SHARD_DEPTH > 0)); then
		for ((i = 0; i < SHARD_DEPTH; i++)); do
			path="$path/${hash:$((i * 2)):2}"
		done
	fi
	printf '%s/%s\n' "$path" "$hash"
}
write_sidecar() {

	DEEBUG "${FUNCNAME[0]}"

	local src="$1"
	local sidecar="$2"

	local size mtime mode
	size=$(stat -c %s "$src")
	mtime=$(stat -c %Y "$src")
	mode=$(stat -c %a "$src")

	mkdir -p "$(dirname "$sidecar")"

	case "$FORMAT" in
	json)
		printf '{"source":"%s","ingested":"%s","size":%s,"mtime":%s,"mode":"%s"}\n' \
			"$src" "$(date -Iseconds)" "$size" "$mtime" "$mode" >"$sidecar"
		;;
	*)
		cat >"$sidecar" <<EOF
<metadata>
  <source>$src</source>
  <ingested>$(date -Iseconds)</ingested>
  <size>$size</size>
  <mtime>$mtime</mtime>
  <mode>$mode</mode>
</metadata>
EOF
		;;
	esac
}

do_dedupe_action() {

	DEEBUG "${FUNCNAME[0]}"

	local origin="$1"
	local incas="$2"

	case "$DEDUPE_ACTION" in
	ignore) ;;
	hardlink)
		rm -f "$origin"
		ln "$incas" "$origin"
		;;
	symlink)
		rm -f "$origin"
		ln -s "$incas" "$origin"
		;;
	reflink)
		cp --preserve=all --reflink=always "$incas" "$origin"
		;;
	delete)
		rm -f "$origin"
		;;
	esac
}

log_dedupe_action() {

	DEEBUG "${FUNCNAME[0]}"

	local src="$1"
	local dst="$2"
	[[ "$DEDUPE_ACTION" == "ignore" ]] && return

	local logfile="$REPO/$DEDUP_SCRIPT_NAME"

	{
		echo "# Duplicate: $src"
		case "$DEDUPE_ACTION" in
		hardlink) echo "rm -f '$src' && ln '$dst' '$src'" ;;
		symlink) echo "rm -f '$src' && ln -s '$dst' '$src'" ;;
		reflink) echo "cp --preserve=all --reflink=always '$dst' '$src'" ;;
		delete) echo "rm -f '$src'" ;;
		esac
		echo
	} >>"$logfile"
}

ingest_method_exec() {

	DEEBUG "${FUNCNAME[0]}"

	local src="$1"
	local dst="$2"

	mkdir -p "$(dirname "$dst")"

	case "$INGEST_METHOD" in
	hardlink)
		ln "$src" "$dst" || {
			printf 'Hardlink failed (filesystem boundary?)\n'
			return 1
		}
		;;
	reflink)
		cp --preserve=all --reflink=always "$src" "$dst"
		;;
	symlink)
		ln -s "$src" "$dst"
		;;
	move)
		mv -vn "$src" "$dst"
		;;
	*)
		printf 'Unknown ingest method\n'
		return 1
		;;
	esac
}

file_into_cas() {

	DEEBUG "${FUNCNAME[0]}"

	local src
	src=$(resolve_path "$1")

	local hash
	hash=$(calculate_hash "$src")

	local cas sidecar
	cas=$(get_storage_path "$hash")
	sidecar="${cas}${SUFFIX}"

	if [[ -e "$cas" ]]; then
		printf 'DUPLICATE -> %s (%s)\n' "${hash:0:8}" "$src"
		log_dedupe_action "$src" "$cas"
		((FORCE == 1)) && do_dedupe_action "$src" "$cas"
		return
	fi

	ingest_method_exec "$src" "$cas"
	write_sidecar "$src" "$sidecar"

	printf 'OK -> %s (%s)\n' "${hash:0:8}" "$src"
}

expand_paths() {

	DEEBUG "${FUNCNAME[0]}"

	local p sub
	for p in "${FILES[@]}"; do
		[[ -L "$p" ]] && continue

		p=$(resolve_path "$p")

		if [[ -f "$p" ]]; then
			file_into_cas "$p"
		elif [[ -d "$p" && $RECURSIVE -eq 1 ]]; then
			while IFS= read -r -d '' sub; do
				[[ -L "$sub" ]] || file_into_cas "$sub"
			done < <(find "$p" -type f -print0)
		fi
	done
}

migrate_structure() {

	DEEBUG "${FUNCNAME[0]}"

	local item name hash target

	while IFS= read -r -d '' item; do
		name=$(basename "$item")

		[[ "$name" == "$CONFIG_FILE" ]] && continue
		[[ "$name" == "$DEDUP_SCRIPT_NAME" ]] && continue

		hash="${name%$SUFFIX}"

		[[ "$hash" =~ ^[a-f0-9]{64,128}$ ]] || continue

		target=$(get_storage_path "$hash")
		[[ "$name" == *"$SUFFIX" ]] && target="${target}${SUFFIX}"

		mkdir -p "$(dirname "$target")"
		[[ "$(resolve_path "$item")" == "$(resolve_path "$(dirname "$target")")/$(basename "$target")" ]] && continue

		mv "$item" "$target"
	done < <(find "$REPO" -type f -print0)

	find "$REPO" -type d -empty -delete
}

main() {
	parse_args "$@"

	[[ -n "$REPO" ]] || {
		printf 'Usage: %s REPO [FILES...]\n' "$0"
		exit 1
	}
	echo "$REPO"
	mkdir -p "$REPO"

	load_config
	save_config

	local dedup_script="$REPO/$DEDUP_SCRIPT_NAME"
	[[ -f "$dedup_script" ]] || printf '#!/usr/bin/env bash\n' >"$dedup_script"

	((MIGRATE_SHARDS == 1)) && migrate_structure
	((${#FILES[@]} > 0)) && expand_paths
}

main "$@"
