#!/usr/bin/env bash
# update_repos.sh — Pull latest changes in already-cloned AVM module repos

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODULES_FILE="${WORKSPACE_ROOT}/.config/modules.yaml"

_usage() {
  cat <<'EOF'
Usage: scripts/update_repos.sh [options]

Options:
  --domain <name>       Filter by a single domain
  --type <res|ptn|utl>  Filter by module type
  -h, --help            Show this help
EOF
}

_valid_type() {
  [[ "$1" == "res" || "$1" == "ptn" || "$1" == "utl" ]]
}

FILTER_DOMAIN=""
FILTER_TYPE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain=*) FILTER_DOMAIN="${1#--domain=}" ;;
    --type=*) FILTER_TYPE="${1#--type=}" ;;
    --domain|--type)
      key="$1"
      shift
      if [[ $# -eq 0 || "${1}" == --* ]]; then
        echo "ERROR: ${key} requires a value" >&2
        _usage
        exit 1
      fi
      case "${key}" in
        --domain) FILTER_DOMAIN="$1" ;;
        --type) FILTER_TYPE="$1" ;;
      esac
      ;;
    -h|--help|help)
      _usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option '$1'" >&2
      _usage
      exit 1
      ;;
  esac
  shift
done

if [[ -n "${FILTER_TYPE}" ]] && ! _valid_type "${FILTER_TYPE}"; then
  echo "ERROR: --type must be one of: res, ptn, utl" >&2
  exit 1
fi

if ! command -v git &>/dev/null; then
  echo "ERROR: 'git' is required but not installed."
  exit 1
fi

if [[ ! -f "${MODULES_FILE}" ]]; then
  echo "ERROR: .config/modules.yaml not found. Run './avm.sh setup' first."
  exit 1
fi

echo ""
echo "Pulling latest changes for cloned module repos..."
echo "────────────────────────────────────────────────────────"

pulled=0
skipped=0
failed=0
current_name=""
current_domain=""
current_type=""

while IFS= read -r line || [[ -n "${line}" ]]; do
  line="${line//$'\r'/}"
  [[ "${line}" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line//[[:space:]]/}" ]] && continue

  if [[ "${line}" =~ ^[[:space:]]*-[[:space:]]name:[[:space:]]+(.*) ]]; then
    current_name="${BASH_REMATCH[1]}"
    current_domain=""
    current_type=""
  elif [[ "${line}" =~ ^[[:space:]]*domain:[[:space:]]+(.*) ]]; then
    current_domain="${BASH_REMATCH[1]}"
  elif [[ "${line}" =~ ^[[:space:]]*type:[[:space:]]+(.*) ]]; then
    current_type="${BASH_REMATCH[1]}"

    [[ -n "${FILTER_DOMAIN}" && "${current_domain}" != "${FILTER_DOMAIN}" ]] && continue
    [[ -n "${FILTER_TYPE}" && "${current_type}" != "${FILTER_TYPE}" ]] && continue

    repo_dir="${WORKSPACE_ROOT}/${current_name}"
    if [[ ! -d "${repo_dir}/.git" ]]; then
      echo "  SKIP  ${current_name}  (not cloned)"
      skipped=$((skipped + 1))
      continue
    fi

    printf "  PULL  %-60s  [%s] (%s)\n" "${current_name}" "${current_type}" "${current_domain}"
    if git -C "${repo_dir}" pull --ff-only --quiet 2>&1; then
      pulled=$((pulled + 1))
    else
      echo "    WARNING: pull failed for ${current_name}"
      failed=$((failed + 1))
    fi
  fi
done < "${MODULES_FILE}"

echo "────────────────────────────────────────────────────────"
echo "Done — pulled: ${pulled}, skipped (not cloned): ${skipped}, failed: ${failed}"
[[ ${failed} -gt 0 ]] && exit 1 || true
