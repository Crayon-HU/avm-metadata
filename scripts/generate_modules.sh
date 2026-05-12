#!/usr/bin/env bash
# generate_modules.sh — Merge selected domain YAML files into .config/modules.yaml
#
# Reads all .config/{domain}.yaml files (excluding modules.yaml itself).
# Prompts the user to select domains interactively, or accepts --domains flag.
#
# Requirements: git (no other dependencies — pure bash YAML generation)
#
# Usage:
#   scripts/generate_modules.sh                                    # interactive menu
#   scripts/generate_modules.sh --domains networking,compute
#   scripts/generate_modules.sh --domains all
#   scripts/generate_modules.sh --domains all --types res
#   scripts/generate_modules.sh --domains networking --types res,ptn

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${WORKSPACE_ROOT}/.config"
OUTPUT_FILE="${CONFIG_DIR}/modules.yaml"

_usage() {
  cat <<'EOF'
Usage: scripts/generate_modules.sh [options]

Options:
  --domains <list|all>   Comma-separated domain names, or 'all'
  --types   <list|all>   Comma-separated types (res,ptn,utl), or 'all'
  -h, --help             Show this help

Examples:
  scripts/generate_modules.sh --domains all
  scripts/generate_modules.sh --domains networking,compute --types res,ptn
EOF
}

# ---------------------------------------------------------------------------
# Discover domain files (bash 3-compatible: no mapfile)
# ---------------------------------------------------------------------------
DOMAIN_FILES=()
while IFS= read -r f; do
  DOMAIN_FILES+=("$f")
done < <(find "${CONFIG_DIR}" -maxdepth 1 -name "*.yaml" ! -name "modules.yaml" ! -name "workspaces.yaml" | sort)

if [[ ${#DOMAIN_FILES[@]} -eq 0 ]]; then
  echo "ERROR: No domain YAML files found in ${CONFIG_DIR}"
  exit 1
fi

# Extract domain slugs from filenames
declare -a DOMAIN_SLUGS=()
for f in "${DOMAIN_FILES[@]}"; do
  slug="$(basename "${f}" .yaml)"
  DOMAIN_SLUGS+=("${slug}")
done

# ---------------------------------------------------------------------------
# Parse --domains and --types flags (or fall through to interactive menu)
# ---------------------------------------------------------------------------
CLI_DOMAINS=""
CLI_TYPES=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domains=*) CLI_DOMAINS="${1#--domains=}" ;;
    --types=*)   CLI_TYPES="${1#--types=}" ;;
    --domains)
      shift
      if [[ $# -eq 0 || "${1}" == --* ]]; then
        echo "ERROR: --domains requires a value" >&2
        _usage
        exit 1
      fi
      CLI_DOMAINS="$1"
      ;;
    --types)
      shift
      if [[ $# -eq 0 || "${1}" == --* ]]; then
        echo "ERROR: --types requires a value" >&2
        _usage
        exit 1
      fi
      CLI_TYPES="$1"
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

declare -a SELECTED_SLUGS=()

if [[ -n "${CLI_DOMAINS}" ]]; then
  # ── CLI mode ──────────────────────────────────────────────────────────────
  if [[ "${CLI_DOMAINS}" == "all" ]]; then
    SELECTED_SLUGS=("${DOMAIN_SLUGS[@]}")
  else
    IFS=',' read -ra requested <<< "${CLI_DOMAINS}"
    for req in "${requested[@]}"; do
      req="${req// /}"  # trim whitespace
      if [[ -z "${req}" ]]; then
        echo "ERROR: Empty domain value in --domains" >&2
        exit 1
      fi
      found=0
      for slug in "${DOMAIN_SLUGS[@]}"; do
        if [[ "${slug}" == "${req}" ]]; then
          SELECTED_SLUGS+=("${slug}")
          found=1
          break
        fi
      done
      if [[ ${found} -eq 0 ]]; then
        echo "ERROR: Unknown domain '${req}'" >&2
        exit 1
      fi
    done
  fi
else
  # ── Interactive menu ───────────────────────────────────────────────────────
  echo ""
  echo "AVM Module Generator"
  echo "════════════════════════════════════════════════════════════"
  echo "Available domains:"
  echo ""
  for i in "${!DOMAIN_SLUGS[@]}"; do
    printf "  %2d)  %s\n" "$((i + 1))" "${DOMAIN_SLUGS[$i]}"
  done
  echo ""
  echo "Enter domain numbers separated by spaces (e.g. 1 3 5),"
  echo "or type 'all' to select all domains."
  echo ""
  read -rp "Selection: " user_input

  if [[ "$(echo "${user_input}" | tr '[:upper:]' '[:lower:]')" == "all" ]]; then
    SELECTED_SLUGS=("${DOMAIN_SLUGS[@]}")
  else
    read -ra choices <<< "${user_input}"
    for choice in "${choices[@]}"; do
      if [[ "${choice}" =~ ^[0-9]+$ ]] && \
         [[ "${choice}" -ge 1 ]] && \
         [[ "${choice}" -le "${#DOMAIN_SLUGS[@]}" ]]; then
        SELECTED_SLUGS+=("${DOMAIN_SLUGS[$((choice - 1))]}")
      else
        echo "WARNING: Invalid selection '${choice}' — skipping"
      fi
    done
  fi
fi

if [[ ${#SELECTED_SLUGS[@]} -eq 0 ]]; then
  echo "No domains selected. Nothing to do."
  exit 0
fi

# ---------------------------------------------------------------------------
# Type selection (res / ptn / utl)
# ---------------------------------------------------------------------------
ALL_TYPES=("res" "ptn" "utl")
TYPE_LABELS=("Resource  (avm-res-*)" "Pattern   (avm-ptn-*)" "Utility   (avm-utl-*)")
declare -a SELECTED_TYPES=()

if [[ -n "${CLI_TYPES}" ]]; then
  if [[ "${CLI_TYPES}" == "all" ]]; then
    SELECTED_TYPES=("${ALL_TYPES[@]}")
  else
    IFS=',' read -ra _requested_types <<< "${CLI_TYPES}"
    for rt in "${_requested_types[@]}"; do
      rt="${rt// /}"
      if [[ -z "${rt}" ]]; then
        echo "ERROR: Empty type value in --types" >&2
        exit 1
      fi
      found=0
      for t in "${ALL_TYPES[@]}"; do
        if [[ "${t}" == "${rt}" ]]; then
          SELECTED_TYPES+=("${t}")
          found=1
          break
        fi
      done
      if [[ ${found} -eq 0 ]]; then
        echo "ERROR: Unknown type '${rt}' — valid: res, ptn, utl" >&2
        exit 1
      fi
    done
  fi
else
  echo ""
  echo "Module types:"
  echo ""
  for i in "${!ALL_TYPES[@]}"; do
    printf "  %2d)  %-4s — %s\n" "$((i + 1))" "${ALL_TYPES[$i]}" "${TYPE_LABELS[$i]}"
  done
  echo ""
  echo "Enter type numbers separated by spaces (e.g. 1 2),"
  echo "or press Enter / type 'all' to include all types."
  echo ""
  read -rp "Type selection [all]: " type_input

  type_input_lower="$(echo "${type_input:-}" | tr '[:upper:]' '[:lower:]')"
  if [[ -z "${type_input// /}" ]] || [[ "${type_input_lower}" == "all" ]]; then
    SELECTED_TYPES=("${ALL_TYPES[@]}")
  else
    read -ra type_choices <<< "${type_input}"
    for tc in "${type_choices[@]}"; do
      if [[ "${tc}" =~ ^[0-9]+$ ]] && \
         [[ "${tc}" -ge 1 ]] && \
         [[ "${tc}" -le "${#ALL_TYPES[@]}" ]]; then
        SELECTED_TYPES+=("${ALL_TYPES[$((tc - 1))]}")
      else
        echo "WARNING: Invalid type selection '${tc}' — skipping"
      fi
    done
  fi
fi

if [[ ${#SELECTED_TYPES[@]} -eq 0 ]]; then
  echo "No types selected. Nothing to do."
  exit 0
fi

echo ""
echo "Selected domains: ${SELECTED_SLUGS[*]}"
echo "Selected types:   ${SELECTED_TYPES[*]}"

# ---------------------------------------------------------------------------
# Build the generated modules.yaml
# ---------------------------------------------------------------------------
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u)"
DOMAINS_LIST="$(IFS=', '; echo "${SELECTED_SLUGS[*]}")"
TYPES_LIST="$(IFS=', '; echo "${SELECTED_TYPES[*]}")"

{
  echo "# AUTO-GENERATED — do not edit manually."
  echo "# Re-run scripts/generate_modules.sh to update."
  echo "# Generated: ${TIMESTAMP}"
  echo "# Domains:   ${DOMAINS_LIST}"
  echo "# Types:     ${TYPES_LIST}"
  echo "#"
  echo "# Source files: .config/{domain}.yaml"
  echo ""
  echo "modules:"
} > "${OUTPUT_FILE}"

TOTAL=0

for slug in "${SELECTED_SLUGS[@]}"; do
  domain_file="${CONFIG_DIR}/${slug}.yaml"

  if [[ ! -f "${domain_file}" ]]; then
    echo "WARNING: Domain file not found: ${domain_file} — skipping"
    continue
  fi

  # Read the domain file, buffer each module block, then emit only those
  # whose type: field matches SELECTED_TYPES.

  in_module=0
  module_count=0
  module_buf=()
  module_type=""
  module_name=""

  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line//$'\r'/}"  # strip Windows CR

    # Skip commented lines
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue

    # New module entry — flush previous buffer first, then start fresh
    if [[ "${line}" =~ ^[[:space:]]*-[[:space:]]name:[[:space:]]+(.*) ]]; then
      if [[ ${in_module} -eq 1 ]] && [[ ${#module_buf[@]} -gt 0 ]]; then
        type_ok=0
        for sel_t in "${SELECTED_TYPES[@]}"; do
          [[ "${sel_t}" == "${module_type}" ]] && type_ok=1 && break
        done
        if [[ ${type_ok} -eq 1 ]]; then
          for bl in "${module_buf[@]}"; do echo "${bl}" >> "${OUTPUT_FILE}"; done
          echo "" >> "${OUTPUT_FILE}"
          module_count=$((module_count + 1))
        fi
      fi
      # Start new buffer with the name line + injected domain field
      in_module=1
      module_buf=()
      module_type=""
      module_name="${BASH_REMATCH[1]}"
      indent="${line%%[-]*}"
      module_buf+=("${line}")
      module_buf+=("${indent}  domain: ${slug}")
      continue
    fi

    # Skip blank source lines (emit will add its own separator)
    [[ -z "${line//[[:space:]]/}" ]] && continue

    if [[ ${in_module} -eq 1 ]]; then
      # Capture the type: value for filtering
      if [[ "${line}" =~ ^[[:space:]]*type:[[:space:]]+(.*) ]]; then
        module_type="${BASH_REMATCH[1]}"
      fi
      module_buf+=("${line}")
    fi
  done < "${domain_file}"

  # Flush the final module in the file
  if [[ ${in_module} -eq 1 ]] && [[ ${#module_buf[@]} -gt 0 ]]; then
    type_ok=0
    for sel_t in "${SELECTED_TYPES[@]}"; do
      [[ "${sel_t}" == "${module_type}" ]] && type_ok=1 && break
    done
    if [[ ${type_ok} -eq 1 ]]; then
      for bl in "${module_buf[@]}"; do echo "${bl}" >> "${OUTPUT_FILE}"; done
      echo "" >> "${OUTPUT_FILE}"
      module_count=$((module_count + 1))
    fi
  fi

  if [[ ${module_count} -gt 0 ]]; then
    echo "  # (end of domain: ${slug})" >> "${OUTPUT_FILE}"
    echo "" >> "${OUTPUT_FILE}"
  fi

  TOTAL=$((TOTAL + module_count))
  echo "  ✓  ${slug}  (${module_count} modules)"
done

echo "────────────────────────────────────────────────────────"
echo "Done — ${TOTAL} modules written to ${OUTPUT_FILE}"

echo ""
echo "Next step:"
echo "  ./avm.sh clone             # clone all modules"
echo "  ./avm.sh clone --domain networking   # clone one domain"
