#!/usr/bin/env bash
# clone_repos.sh — Clone AVM module repositories listed in .config/modules.yaml
#
# Reads the generated .config/modules.yaml (run scripts/generate_modules.sh first).
# Clones each repo into the workspace root as its name (terraform-azurerm-avm-*/).
# Existing directories are skipped; failed clones are warned and counted.
#
# Requirements: git (no other dependencies — pure bash YAML parsing)
#
# Usage:
#   scripts/clone_repos.sh                         # clone all modules
#   scripts/clone_repos.sh --domain networking     # filter by domain
#   scripts/clone_repos.sh --type ptn              # filter by type (res|ptn|utl)
#   scripts/clone_repos.sh --domain networking --type res
#   scripts/clone_repos.sh --full                  # full history (default: --depth 1)
#   scripts/clone_repos.sh --git-name "Name" --git-email "email@example.com"

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODULES_FILE="${WORKSPACE_ROOT}/.config/modules.yaml"

_usage() {
  cat <<'EOF'
Usage: scripts/clone_repos.sh [options]

Options:
  --domain <name>       Filter by a single domain
  --type <res|ptn|utl>  Filter by module type
  --full                Clone full history instead of shallow depth 1
  --git-name <name>     Set git user.name in cloned repos
  --git-email <email>   Set git user.email in cloned repos
  -h, --help            Show this help
EOF
}

_valid_type() {
  [[ "$1" == "res" || "$1" == "ptn" || "$1" == "utl" ]]
}

# ---------------------------------------------------------------------------
# Parse CLI flags
# ---------------------------------------------------------------------------
FILTER_DOMAIN=""
FILTER_TYPE=""
CLONE_DEPTH="--depth 1"
GIT_NAME=""
GIT_EMAIL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain=*) FILTER_DOMAIN="${1#--domain=}"; shift ;;
    --type=*)   FILTER_TYPE="${1#--type=}"; shift ;;
    --git-name=*) GIT_NAME="${1#--git-name=}"; shift ;;
    --git-email=*) GIT_EMAIL="${1#--git-email=}"; shift ;;
    --domain|--type|--git-name|--git-email)
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
        --git-name) GIT_NAME="$1" ;;
        --git-email) GIT_EMAIL="$1" ;;
      esac
      shift
      ;;
    --full) CLONE_DEPTH=""; shift ;;
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
done

if [[ -n "${FILTER_TYPE}" ]] && ! _valid_type "${FILTER_TYPE}"; then
  echo "ERROR: --type must be one of: res, ptn, utl" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
if ! command -v git &>/dev/null; then
  echo "ERROR: 'git' is required but not installed."
  exit 1
fi

if [[ ! -f "${MODULES_FILE}" ]]; then
  echo "ERROR: .config/modules.yaml not found."
  echo ""
  echo "Generate it first by running:"
  echo "  scripts/generate_modules.sh"
  exit 1
fi

# ---------------------------------------------------------------------------
# Parse modules.yaml — pure bash
#
# Fields collected per module block:
#   _name, _type, _domain, _url, _branch
# A block starts at "  - name:" and is emitted when the next block starts
# or EOF is reached.
# ---------------------------------------------------------------------------
declare -a NAMES=()
declare -a TYPES=()
declare -a DOMAINS=()
declare -a URLS=()
declare -a BRANCHES=()

_name="" _type="" _domain="" _url="" _branch="main"

_emit_module() {
  [[ -n "${_name}" && -n "${_url}" ]] || return 0

  # Apply filters
  if [[ -n "${FILTER_DOMAIN}" && "${_domain}" != "${FILTER_DOMAIN}" ]]; then
    return 0
  fi
  if [[ -n "${FILTER_TYPE}" && "${_type}" != "${FILTER_TYPE}" ]]; then
    return 0
  fi

  NAMES+=("${_name}")
  TYPES+=("${_type}")
  DOMAINS+=("${_domain}")
  URLS+=("${_url}")
  BRANCHES+=("${_branch}")
}

while IFS= read -r line || [[ -n "${line}" ]]; do
  line="${line//$'\r'/}"
  [[ "${line}" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line//[[:space:]]/}" ]] && continue

  if [[ "${line}" =~ ^[[:space:]]*-[[:space:]]name:[[:space:]]+(.*) ]]; then
    _emit_module
    _name="${BASH_REMATCH[1]}"
    _type="" _domain="" _url="" _branch="main"
  elif [[ "${line}" =~ ^[[:space:]]+type:[[:space:]]+(.*) ]]; then
    _type="${BASH_REMATCH[1]}"
  elif [[ "${line}" =~ ^[[:space:]]+domain:[[:space:]]+(.*) ]]; then
    _domain="${BASH_REMATCH[1]}"
  elif [[ "${line}" =~ ^[[:space:]]+url:[[:space:]]+(.*) ]]; then
    _url="${BASH_REMATCH[1]}"
  elif [[ "${line}" =~ ^[[:space:]]+branch:[[:space:]]+(.*) ]]; then
    _branch="${BASH_REMATCH[1]}"
  fi
done < "${MODULES_FILE}"
_emit_module  # flush last entry

# ---------------------------------------------------------------------------
# Print effective filters
# ---------------------------------------------------------------------------
MODULE_COUNT="${#NAMES[@]}"

if [[ ${MODULE_COUNT} -eq 0 ]]; then
  echo "No modules match the specified filters. Nothing to clone."
  [[ -n "${FILTER_DOMAIN}" ]] && echo "  --domain=${FILTER_DOMAIN}"
  [[ -n "${FILTER_TYPE}" ]]   && echo "  --type=${FILTER_TYPE}"
  exit 0
fi

echo "AVM clone — ${MODULE_COUNT} modules"
echo "Workspace root: ${WORKSPACE_ROOT}"
[[ -n "${FILTER_DOMAIN}" ]] && echo "Domain filter:  ${FILTER_DOMAIN}"
[[ -n "${FILTER_TYPE}" ]]   && echo "Type filter:    ${FILTER_TYPE}"
[[ -z "${CLONE_DEPTH}" ]]   && echo "Clone mode:     full history" || echo "Clone mode:     shallow (--depth 1)"
echo "────────────────────────────────────────────────────────"

# ---------------------------------------------------------------------------
# Clone repos
# ---------------------------------------------------------------------------
CLONED=0
SKIPPED=0
FAILED=0

for i in "${!NAMES[@]}"; do
  NAME="${NAMES[$i]}"
  URL="${URLS[$i]}"
  BRANCH="${BRANCHES[$i]}"
  TYPE="${TYPES[$i]}"
  DOMAIN="${DOMAINS[$i]}"
  TARGET="${WORKSPACE_ROOT}/${NAME}"

  TYPE_LABEL="[${TYPE}]"
  DOMAIN_LABEL="(${DOMAIN})"

  if [[ -d "${TARGET}/.git" ]]; then
    echo "- SKIP   ${NAME}  ${TYPE_LABEL} ${DOMAIN_LABEL}"
    SKIPPED=$((SKIPPED + 1))

    # Set local git identity on pre-existing repos if requested
    if [[ -n "${GIT_NAME}" ]]; then
      git -C "${TARGET}" config user.name "${GIT_NAME}" 2>/dev/null || true
    fi
    if [[ -n "${GIT_EMAIL}" ]]; then
      git -C "${TARGET}" config user.email "${GIT_EMAIL}" 2>/dev/null || true
    fi
  else
    echo "↓ CLONE ${NAME}  ${TYPE_LABEL} ${DOMAIN_LABEL}"
    # shellcheck disable=SC2086
    if git clone ${CLONE_DEPTH} --branch "${BRANCH}" "${URL}" "${TARGET}" 2>&1; then
      if [[ -n "${GIT_NAME}" ]]; then
        git -C "${TARGET}" config user.name  "${GIT_NAME}"
      fi
      if [[ -n "${GIT_EMAIL}" ]]; then
        git -C "${TARGET}" config user.email "${GIT_EMAIL}"
      fi
      CLONED=$((CLONED + 1))
    else
      echo "  WARNING: clone failed for ${NAME}"
      FAILED=$((FAILED + 1))
    fi
  fi
done

echo "────────────────────────────────────────────────────────"
echo "Done — cloned: ${CLONED}, skipped: ${SKIPPED}, failed: ${FAILED}"
[[ ${FAILED} -eq 0 ]] || exit 1
