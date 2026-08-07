#!/usr/bin/env bash
# macOS/Linux machine bootstrap. Mirrors bootstrap-windows.ps1 from the
# original Windows toolkit, but targets a POSIX venv layout (.venv/bin/python)
# and does not attempt to auto-provision an X-13 binary (see note below).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REQUESTED_PYTHON="${1:-}"
VENV="$ROOT/.venv"
VENV_PYTHON="$VENV/bin/python"
ERRORS=()

echo "Isan Household Financial Fragility Toolkit - machine setup"
echo "Repo: $ROOT"

find_python() {
  if [[ -n "$REQUESTED_PYTHON" ]]; then
    command -v "$REQUESTED_PYTHON"
    return
  fi
  for name in python3.13 python3.12 python3.11 python3; do
    if command -v "$name" >/dev/null 2>&1; then
      local v
      v="$("$name" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
      case "$v" in
        3.11.*|3.12.*|3.13.*) command -v "$name"; return ;;
      esac
    fi
  done
  echo "Python 3.11-3.13 not found. Install Python 3.11-3.13, then rerun." >&2
  exit 1
}

BASE_PYTHON="$(find_python)"
echo "PASS Base Python: $BASE_PYTHON ($("$BASE_PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'))"

if [[ ! -x "$VENV_PYTHON" ]]; then
  if [[ -d "$VENV" ]]; then
    echo "Existing .venv is incomplete: $VENV. Remove or repair it, then rerun." >&2
    exit 1
  fi
  "$BASE_PYTHON" -m venv "$VENV"
  echo "Created $VENV"
fi

"$VENV_PYTHON" -m pip install --disable-pip-version-check --requirement "$ROOT/requirements-analysis.txt"
"$VENV_PYTHON" -c "import numpy, pandas, scipy, statsmodels; print(f'PASS Analysis dependencies: numpy={numpy.__version__}, pandas={pandas.__version__}, scipy={scipy.__version__}, statsmodels={statsmodels.__version__}')"

# --- X-13ARIMA-SEATS -------------------------------------------------------
# Unlike Windows, the U.S. Census Bureau does not publish a prebuilt macOS
# binary we can download and hash-verify automatically. Compile the ASCII
# variant from Census's official Fortran source (tested and working, see
# README.md "แพลตฟอร์มและ X-13" for the exact commands):
#   https://www2.census.gov/software/x-13arima-seats/x13as/unix-linux/program-archives/x13as_asciisrc-v1-1-b62.tar.gz
# Do NOT use the R package `x13binary` (CRAN) even though it bundles a macOS
# binary — that binary is the `x13ashtml` variant (for R's `seasonal`
# package, which parses HTML), it only writes .html reports and never
# produces the .d11/.out files analysis/x13.py reads. Confirmed broken here.
# Whichever path, expose it as `x13as` on PATH or place it at
# .tools/x13/1.1-b62/x13as (chmod +x). analysis/x13.py checks both locations.
X13_LOCAL="$ROOT/.tools/x13/1.1-b62/x13as"
if [[ -x "$X13_LOCAL" ]]; then
  echo "PASS Repo-local X-13: $X13_LOCAL"
elif command -v x13as >/dev/null 2>&1; then
  echo "PASS X-13 on PATH: $(command -v x13as)"
else
  ERRORS+=("X-13 binary not found. See the note above this line in scripts/bootstrap-mac.sh for install options; analysis/build.py will fail until one is in place.")
fi

# --- Git ---------------------------------------------------------------
if ! command -v git >/dev/null 2>&1; then
  ERRORS+=("Git not found")
else
  if REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    echo "PASS Git repository: $REPO_ROOT"
  else
    ERRORS+=("This folder is not a Git clone")
  fi
  AUTHOR_NAME="$(git config user.name || true)"
  AUTHOR_EMAIL="$(git config user.email || true)"
  if [[ -z "$AUTHOR_NAME" || -z "$AUTHOR_EMAIL" ]]; then
    ERRORS+=("Git author missing; set git config user.name and user.email")
  else
    echo "PASS Git author: $AUTHOR_NAME <$AUTHOR_EMAIL>"
  fi
fi

# --- Chrome --------------------------------------------------------------
CHROME_CANDIDATES=(
  "/Applications/Google Chrome.app"
  "$HOME/Applications/Google Chrome.app"
)
CHROME_FOUND=""
for c in "${CHROME_CANDIDATES[@]}"; do
  if [[ -d "$c" ]]; then CHROME_FOUND="$c"; break; fi
done
if [[ -z "$CHROME_FOUND" ]]; then
  ERRORS+=("Google Chrome not found in /Applications")
else
  echo "PASS Google Chrome: $CHROME_FOUND"
fi

# --- GitHub CLI ------------------------------------------------------------
if ! command -v gh >/dev/null 2>&1; then
  ERRORS+=("GitHub CLI not found; install gh and run gh auth login")
else
  if gh auth status >/dev/null 2>&1; then
    echo "PASS GitHub authentication"
  else
    ERRORS+=("GitHub CLI is not signed in; run gh auth login and gh auth setup-git")
  fi
fi

# --- Dataset checks (only if nothing fatal so far) --------------------------
if [[ ${#ERRORS[@]} -eq 0 ]]; then
  if "$VENV_PYTHON" collector/audit.py --strict; then
    echo "PASS Dataset structural audit"
  else
    ERRORS+=("Dataset structural audit failed")
  fi

  if "$VENV_PYTHON" collector/build_site_data.py --check; then
    echo "PASS Generated site data check"
  else
    ERRORS+=("Generated site data check failed")
  fi

  if "$VENV_PYTHON" -m analysis.build --audit; then
    echo "PASS Analytical output audit"
  else
    ERRORS+=("Analytical output audit failed")
  fi

  if "$VENV_PYTHON" -m unittest discover -s tests -v; then
    echo "PASS Full unit tests"
  else
    ERRORS+=("Unit tests failed")
  fi
fi

if [[ ${#ERRORS[@]} -gt 0 ]]; then
  echo ""
  echo "NOT READY"
  for e in "${ERRORS[@]}"; do echo "- $e"; done
  exit 1
fi

echo ""
echo "MACHINE READY"
echo "Python environment: $VENV_PYTHON"
echo "One-time Chrome setup still requires the user:"
echo "1. Load unpacked extension from: $ROOT/extension"
echo "2. Allow trends.google.co.th and set Chrome Downloads to: $ROOT/incoming"
echo "3. Turn off 'Ask where to save each file'"
echo ""
echo "Monthly prepare: ./scripts/toolkit.sh monthly-prepare"
echo "Monthly finish:  ./scripts/toolkit.sh monthly-finish"
echo "Queue file: $ROOT/extension/data/jobs.json"
