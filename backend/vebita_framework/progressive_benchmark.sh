#!/bin/bash
# progressive_benchmark.sh
#
# Runs VEBITA's run_benchmark.py against the real Movebank CSVs sitting in
# backend/uploads, smallest file first, biggest file last, so you can watch
# how the 511 algorithms behave as data size grows on this machine.
#
# Each run is time-boxed (default 20 min) and its wall-clock time + peak
# memory are appended to results/progressive/summary.csv, so you get one
# scaling table at the end even if a big file times out.
#
# Works on both macOS (BSD stat/time) and Linux (GNU stat/time) - it
# auto-detects which one it's running on.
#
# Usage:
#   ./progressive_benchmark.sh                  # run the whole progression, smallest->biggest
#   ./progressive_benchmark.sh --jobs 4         # override parallel workers (default 2)
#   ./progressive_benchmark.sh --timeout 1800   # override per-file time limit, in seconds
#   ./progressive_benchmark.sh --only 5         # run just item #5 (1-indexed, see list below)
#   ./progressive_benchmark.sh --from 6         # start at item #6 and continue to the end

set -uo pipefail
set -m   # job control on, so we can kill a whole process group on timeout

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

UPLOAD_DIR="$SCRIPT_DIR/../uploads"
RESULTS_DIR="$SCRIPT_DIR/results/progressive"
LOG_DIR="$RESULTS_DIR/logs"
SUMMARY="$RESULTS_DIR/summary.csv"

# Use whichever python3 is on PATH (activate your venv, or prefix PATH, before running).
PYTHON_BIN="${PYTHON_BIN:-python3}"

JOBS=1   # jobs>1 uses joblib multiprocessing, which segfaults in some sandboxed shells - bump this up if you run natively in Terminal.app
TIMEOUT=1200   # 20 minutes per file by default
ONLY=""
FROM=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --jobs) JOBS="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --from) FROM="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

mkdir -p "$RESULTS_DIR" "$LOG_DIR"

# ---- OS-specific stat / time handling -------------------------------------
OS_NAME="$(uname -s)"
stat_size() {
  if [[ "$OS_NAME" == "Darwin" ]]; then
    stat -f%z "$1"
  else
    stat -c%s "$1"
  fi
}
peak_mem_mb() {
  # $1 = log file. Echoes peak RSS in MB, or "?" if not found.
  local log="$1"
  if [[ "$OS_NAME" == "Darwin" ]]; then
    local b
    b=$(grep "maximum resident set size" "$log" | awk '{print $1}')
    [[ -n "${b:-}" ]] && echo $(( b / 1048576 )) || echo "?"
  else
    local kb
    kb=$(grep "Maximum resident set size" "$log" | awk -F': ' '{print $2}' | tr -d ' ')
    [[ -n "${kb:-}" ]] && echo $(( kb / 1024 )) || echo "?"
  fi
}
time_wrap() {
  # Prints the /usr/bin/time invocation as separate words (use with "$@" expansion via array)
  if [[ "$OS_NAME" == "Darwin" ]]; then
    echo "/usr/bin/time -l"
  else
    echo "/usr/bin/time -v"
  fi
}
read -r -a TIME_CMD <<< "$(time_wrap)"

# The 6 unique real datasets actually in backend/uploads, smallest -> biggest.
# (Two other files there are byte-identical duplicates of #1 and #6 - skipped.)
LABELS=(
  "01_orchid_bees_21KB"
  "02_black_guillemot_487KB"
  "03_african_cuckoo_1.5MB"
  "04_whooper_swan_17.6MB"
  "05_jackal_18.9MB"
  "06_white_stork_tunisia_45.4MB"
  "07_african_elephants_516MB"
  "08_white_stork_bavaria_1.87GB"
)
FILES=(
  "6cf5570789fa45b6829e7b13c4409ba5_Orchid bees on Barro Colorado Island, Panama.csv"
  "6144589754334ee4b21a77b4d2c6f2b7_BTO - Bangor 2021 - Black Guillemot.csv"
  "7968800f8abb4990af5de0d18ed958ab_African cuckoo in Nigeria (data from Iwajomo et al. 2018).csv"
  "9a52efaf8ac54dcd8873a08999f71576_LifeTrack Whooper Swan Latvia.csv"
  "6eadf3061e964283850eb06a2874a617_Black-backed jackal, Etosha National Park, Namibia.csv"
  "133303b9f2014a56b83eec7b0999db4a_LifeTrack White Stork Tunisia.csv"
  "d16c121743ff4c54a858eb62bf3ceac8_African elephants in Etosha National Park (data from Tsalyuk et al. 2018).csv"
  "c7a3c12cbd9a4c299dfd777c2f52a075_LifeTrack White Stork Bavaria.csv"
)

if [[ ! -f "$SUMMARY" ]]; then
  echo "label,file,size_bytes,size_human,elapsed_s,peak_mem_mb,outcome" > "$SUMMARY"
fi

# Preflight: make sure the needed packages are importable on whatever python3
# is on PATH right now (activate your venv before running this script).
"$PYTHON_BIN" -c "import numpy, pandas, sklearn, scipy, joblib, statsmodels, filterpy" 2>/tmp/preflight_err.txt
if [[ $? -ne 0 ]]; then
  echo "Missing Python packages for: $(command -v "$PYTHON_BIN")"
  echo
  echo "  cd \"$SCRIPT_DIR\""
  echo "  python3 -m venv venv_mac"
  echo "  source venv_mac/bin/activate   # then re-run this script"
  echo "  pip install --upgrade pip"
  echo "  pip install -r requirements.txt -r ../requirements.txt"
  echo
  echo "(error was: $(cat /tmp/preflight_err.txt))"
  exit 1
fi

run_one() {
  local idx=$1
  local file="${FILES[$idx]}"
  local label="${LABELS[$idx]}"
  local csv_path="$UPLOAD_DIR/$file"
  local out_csv="$RESULTS_DIR/${label}.csv"
  local log_file="$LOG_DIR/${label}.log"

  if [[ ! -f "$csv_path" ]]; then
    echo "[$label] SKIP - file not found: $csv_path"
    return
  fi

  local size_bytes size_human
  size_bytes=$(stat_size "$csv_path")
  size_human=$(du -h "$csv_path" | cut -f1 | tr -d ' ')

  echo "=========================================="
  echo "[$label]  size=$size_human  jobs=$JOBS  timeout=${TIMEOUT}s  python=$(command -v "$PYTHON_BIN")"
  echo "file: $file"
  echo "=========================================="

  local t_start t_end elapsed status
  t_start=$(date +%s)

  (
    export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONIOENCODING=utf-8
    exec "${TIME_CMD[@]}" "$PYTHON_BIN" run_benchmark.py \
      --csv "$csv_path" --jobs "$JOBS" --output "$out_csv"
  ) > "$log_file" 2>&1 &
  local pid=$!

  ( sleep "$TIMEOUT"; kill -9 -"$pid" 2>/dev/null ) &
  local watchdog=$!

  wait "$pid" 2>/dev/null
  status=$?
  kill "$watchdog" 2>/dev/null; wait "$watchdog" 2>/dev/null

  t_end=$(date +%s)
  elapsed=$((t_end - t_start))

  local peak_mb
  peak_mb=$(peak_mem_mb "$log_file")

  local outcome="ok"
  if [[ $elapsed -ge $TIMEOUT ]]; then
    outcome="TIMEOUT_KILLED_after_${TIMEOUT}s"
  elif [[ $status -ne 0 ]]; then
    outcome="FAILED(exit=$status)"
  fi

  echo "${label},${file},${size_bytes},${size_human},${elapsed},${peak_mb},${outcome}" >> "$SUMMARY"
  echo "-> elapsed=${elapsed}s  peak_mem=${peak_mb}MB  outcome=${outcome}"
  echo "   full log: $log_file"
  echo
}

if [[ -n "$ONLY" ]]; then
  run_one $((ONLY - 1))
else
  for ((i = FROM - 1; i < ${#FILES[@]}; i++)); do
    run_one "$i"
  done
fi

echo "Done. Scaling summary: $SUMMARY"
column -s, -t "$SUMMARY" 2>/dev/null || cat "$SUMMARY"
