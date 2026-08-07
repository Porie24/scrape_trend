#!/usr/bin/env bash
# macOS/Linux port of scripts/toolkit.ps1 from the original Windows toolkit.
# Usage: ./scripts/toolkit.sh <setup|monthly-prepare|monthly-finish|monthly-run|add-keyword> [args...]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VENV_PYTHON="$ROOT/.venv/bin/python"

ACTION="${1:-}"
shift || true

assert_venv_python() {
  if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Analysis environment not found. Run './scripts/toolkit.sh setup' first." >&2
    exit 1
  fi
}

invoke_native() {
  local label="$1"; shift
  echo "==> $label"
  if ! "$@"; then
    local code=$?
    # 9 means a guard stopped on purpose and already explained itself in Thai.
    if [[ $code -eq 9 ]]; then exit 9; fi
    echo "$label failed with exit code $code" >&2
    exit "$code"
  fi
}

monthly_prepare() {
  assert_venv_python
  local job_args=("$@")
  if [[ ${#job_args[@]} -eq 0 ]]; then
    job_args=("--all")
  fi
  invoke_native "Create extension queue" "$VENV_PYTHON" collector/make_jobs.py "${job_args[@]}"
  echo ""
  echo "QUEUE READY"
  echo "In Chrome Controller: Import jobs.json, choose the file shown above, press Start."
}

monthly_finish() {
  local latest_month="${1:-}"
  assert_venv_python
  invoke_native "Validate incoming files (dry run)" "$VENV_PYTHON" collector/ingest.py --dry-run
  invoke_native "Ingest incoming files" "$VENV_PYTHON" collector/ingest.py
  invoke_native "Audit raw dataset structure" "$VENV_PYTHON" collector/audit.py --strict

  if [[ -n "$latest_month" ]]; then
    invoke_native "Audit raw dataset freshness" "$VENV_PYTHON" collector/audit.py --strict --require-latest "$latest_month"
  else
    invoke_native "Audit raw dataset freshness" "$VENV_PYTHON" collector/audit.py --strict --require-latest
  fi

  invoke_native "Verify generated site data" "$VENV_PYTHON" collector/build_site_data.py --check
  invoke_native "Build analytical outputs" "$VENV_PYTHON" -m analysis.build
  invoke_native "Byte-check analytical outputs" "$VENV_PYTHON" -m analysis.build --check
  invoke_native "Audit analytical outputs" "$VENV_PYTHON" -m analysis.build --audit
  invoke_native "Run full test suite" "$VENV_PYTHON" -m unittest discover -s tests -v

  invoke_native "Show release working tree" git status --short
  echo ""
  echo "MONTHLY CHECKS PASSED"
  echo "Tableau source: derived/sa_pipeline_v3/series.csv"
  echo "Nothing was staged, committed, pushed, or deployed. Review git status before publishing."
}

chrome_checkpoint() {
  echo ""
  echo "CHROME CHECKPOINT"
  echo "1. Import the queue shown above and press Start."
  echo "2. Resolve CAPTCHA if prompted."
  echo "3. Continue only when the Controller has 0 FAILED jobs and the CSV files are in incoming/."
  read -r -p "Type FINISH to continue: " confirmation
  [[ "$confirmation" == "FINISH" ]]
}

case "$ACTION" in
  setup)
    "$ROOT/scripts/bootstrap-mac.sh" "$@"
    ;;

  monthly-prepare)
    monthly_prepare "$@"
    ;;

  monthly-finish)
    latest="${1:-}"
    monthly_finish "$latest"
    ;;

  monthly-run)
    monthly_prepare "$@"
    if chrome_checkpoint; then
      monthly_finish ""
      echo "MONTHLY LOOP COMPLETE"
    else
      echo "MONTHLY LOOP STOPPED before ingest. Re-run monthly-run when ready."
    fi
    ;;

  add-keyword)
    assert_venv_python
    id_file="$(mktemp -t gt-new-keyword)"
    trap 'rm -f "$id_file"' EXIT
    invoke_native "Add the keyword" "$VENV_PYTHON" collector/add_keyword.py --interactive --id-file "$id_file"
    if [[ ! -s "$id_file" ]]; then
      echo "The keyword was not added" >&2
      exit 1
    fi
    keyword_id="$(tr -d '[:space:]' < "$id_file")"

    monthly_prepare --ids "$keyword_id"

    if chrome_checkpoint; then
      invoke_native "Screen the keyword and set its tier" "$VENV_PYTHON" collector/add_keyword.py --finalize "$keyword_id"
      monthly_finish ""
      echo "NEW KEYWORD READY"
      echo "Publish with keywords.csv included in the staged allowlist."
    else
      echo "STOPPED before screening. The row stays in keywords.csv."
      echo "Remove it with: collector/add_keyword.py --remove $keyword_id"
    fi
    ;;

  *)
    echo "Usage: $0 <setup|monthly-prepare|monthly-finish|monthly-run|add-keyword> [args...]" >&2
    exit 1
    ;;
esac
